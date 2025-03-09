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
                    if idx > 0 and not (min_val <= e["value"] <= max_val):
                        anomalies_list.append(anomaly_data)
                else:  # monotonicity
                    if idx >= context_size and idx < len(points) - context_size:
                        context_values = (
                            [p[1] for p in anomaly_data["context_before"][::-1]]
                            + [e["value"]]
                            + [p[1] for p in anomaly_data["context_after"]]
                        )
                        before_vals = context_values[:context_size]
                        after_vals = context_values[context_size + 1 :]
                        curr_val = e["value"]
                        if (before_vals and curr_val < max(before_vals)) or (
                            after_vals
                            and curr_val > min(after_vals)
                            and any(v < curr_val for v in after_vals)
                        ):
                            anomalies_list.append(anomaly_data)

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
            result = self.client.write_points(json_body)
            if result:
                anomaly["value"] = fix_value  # Update in memory
                success_count += 1
            else:
                errors.append(f"Failed to write fix for {anomaly['time']}")

        return success_count, errors
