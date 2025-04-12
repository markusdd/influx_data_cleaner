from influxdb import InfluxDBClient


class DataManager:
    """Handles data operations with InfluxDB."""

    def __init__(self, client: InfluxDBClient):
        self.client = client
        self.anomalies = []

    def scan_data(
        self,
        unit: str,
        entity_id: str,
        start_time: str,
        end_time: str,
        context_size: int,
        check_type: str,
        min_val: float,
        max_val: float,
    ):
        """Scan InfluxDB for anomalies based on bounds or monotonicity."""
        self.anomalies.clear()
        query = (
            f'SELECT value, friendly_name FROM "{unit}" WHERE '
            f"(\"entity_id\" = '{entity_id}') AND "
            f"time > now(){start_time} AND "
            f"time < now(){end_time} GROUP BY *"
        )

        result = self.client.query(query)

        anomalies_list = []
        last_flagged_idx = -2  # Track the index of the last flagged anomaly to avoid consecutive flagging

        for p in result:
            points = list(p)
            for idx, e in enumerate(points):
                anomaly_data = {
                    "time": e["time"],
                    "value": e["value"],
                    "prev_value": points[max(0, idx - 1)]["value"] if idx > 0 else None,
                    "next_value": (
                        points[min(len(points) - 1, idx + 1)]["value"]
                        if idx < len(points) - 1
                        else None
                    ),
                    "measurement": unit,
                    "entity_id": entity_id,
                    "friendly_name": e.get("friendly_name", None),
                    "context_before": [],
                    "context_after": [],
                }

                for i in range(1, context_size + 1):
                    if idx - i >= 0:
                        anomaly_data["context_before"].append(
                            (points[idx - i]["time"], points[idx - i]["value"])
                        )
                    if idx + i < len(points):
                        anomaly_data["context_after"].append(
                            (points[idx + i]["time"], points[idx + i]["value"])
                        )

                if check_type == "bounds":
                    if not (min_val <= e["value"] <= max_val):
                        anomalies_list.append(anomaly_data)
                        last_flagged_idx = idx
                else:  # monotonicity
                    if idx > 0 and idx < len(points) - 1:  # Ensure prev and next exist
                        curr_val = e["value"]
                        prev_val = anomaly_data["prev_value"]
                        next_val = anomaly_data["next_value"]
                        before_vals = [p[1] for p in anomaly_data["context_before"][::-1]]
                        after_vals = [p[1] for p in anomaly_data["context_after"]]

                        # Skip if no context to establish trend
                        if not before_vals or not after_vals:
                            continue

                        # Establish trend boundaries from context
                        max_before = max(before_vals)
                        min_before = min(before_vals)
                        max_after = max(after_vals)
                        min_after = min(after_vals)

                        # Detect isolated peaks and dips using full context
                        is_peak = curr_val > prev_val and curr_val > next_val
                        is_dip = curr_val < prev_val and curr_val < next_val

                        # Flag as anomaly if it's a dip or a significant peak
                        should_flag = False
                        if is_dip:
                            # Flag dips that are below the trend
                            if curr_val < max_before and curr_val < min_after:
                                # Avoid flagging if this is a correction after a peak
                                if idx != last_flagged_idx + 1:  # Not immediately after a flagged anomaly
                                    should_flag = True
                                elif curr_val >= min_before:  # Aligns with pre-anomaly trend
                                    should_flag = False
                                else:
                                    should_flag = True  # Flag if it's a new dip below the trend
                        elif is_peak:
                            # Flag peaks that are above both the trend before and after
                            if curr_val > max_before and curr_val > max_after:
                                if idx != last_flagged_idx + 1:  # Not immediately after a flagged anomaly
                                    should_flag = True
                                elif curr_val > max(before_vals[:-1] if len(before_vals) > 1 else before_vals):  # Still above pre-anomaly trend
                                    should_flag = True

                        if should_flag:
                            anomalies_list.append(anomaly_data)
                            last_flagged_idx = idx

        self.anomalies = anomalies_list
        return anomalies_list

    def delete_selected(self, selected_indices: list) -> int:
        """Delete selected anomalies from InfluxDB."""
        if not selected_indices:
            return 0

        deleted_count = 0
        for idx in selected_indices:
            anomaly = self.anomalies[idx]
            dquery = (
                f'DELETE FROM "{anomaly["measurement"]}" WHERE '
                f'("entity_id" = \'{anomaly["entity_id"]}\') AND '
                f'(time = \'{anomaly["time"]}\')'
            )
            self.client.query(dquery)
            deleted_count += 1

        return deleted_count

    def fix_selected(self, selected_indices: list, fix_method: str) -> tuple[int, list]:
        """Fix selected anomalies in InfluxDB using the specified method."""
        if not selected_indices:
            return 0, []

        success_count = 0
        errors = []
        for idx in selected_indices:
            anomaly = self.anomalies[idx]

            if fix_method == "Previous Value":
                fix_value = anomaly["prev_value"]
            elif fix_method == "Next Value":
                fix_value = anomaly["next_value"]
            elif fix_method == "Average of Previous and Next":
                if (
                    anomaly["prev_value"] is not None
                    and anomaly["next_value"] is not None
                ):
                    fix_value = (anomaly["prev_value"] + anomaly["next_value"]) / 2
                else:
                    errors.append(
                        f"Cannot average for {anomaly['time']}: Missing previous or next value"
                    )
                    continue

            if fix_value is None:
                errors.append(
                    f"No {fix_method.lower()} available for {anomaly['time']}"
                )
                continue

            json_body = [
                {
                    "measurement": anomaly["measurement"],
                    "tags": {
                        "domain": "sensor",
                        "entity_id": anomaly["entity_id"],
                        "source": "HA",
                        "friendly_name": anomaly["friendly_name"],
                    },
                    "time": anomaly["time"],
                    "fields": {"value": fix_value},
                }
            ]
            print(json_body)
            result = self.client.write_points(json_body)
            if result:
                anomaly["value"] = fix_value  # Update in memory
                success_count += 1
            else:
                errors.append(f"Failed to write fix for {anomaly['time']}")

        return success_count, errors
