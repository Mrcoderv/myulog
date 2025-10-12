# Field Inventory Template

This template defines the core fields expected in ULog synthetic logs.  
Each field includes a description, type, example, and whether it is required.


| Field Name     | Description                          | Type      | Example                  | Required |
|----------------|--------------------------------------|-----------|--------------------------|----------|
| `timestamp`    | Event time in UTC (ISO 8601)         | datetime  | `2025-10-12T12:31:45Z`   | Yes      |
| `log_level`    | Log severity level                   | enum      | `INFO`                   | Yes      |
| `event_id`     | Unique event identifier              | string    | `evt-12345`              | Yes      |
| `service_name` | Originating system or microservice   | string    | `payment_api`            | Yes      |
| `user_id`      | User identifier (hashed/anonymized)  | string    | `user-98765`             | No       |
| `status_code`  | HTTP/system status code              | integer   | `200`                    | No       |
| `response_time`| Time taken in ms                     | float     | `123.45`                 | No       |
| `message`      | Log message content                  | string    | `"Payment processed"`    | No       |
| `error_flag`   | Error indicator                      | boolean   | `true`                   | No       |
