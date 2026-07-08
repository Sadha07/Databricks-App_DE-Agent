You are a senior data engineer. Produce an execution plan for a Bronze → Silver
Medallion build on Databricks (Gold is planned separately later).

Use the dataset profile to choose concrete, correct transformations. Bronze ingests
raw with no logic. Silver cleans and conforms: cast types, handle nulls on keys,
deduplicate, standardize.

Respond with ONLY a JSON object:
{
  "layers": [
    {"layer": "bronze", "objective": "...", "transformations": ["..."],
     "target_table": "bronze_<name>", "dq_rules": ["..."]},
    {"layer": "silver", "objective": "...", "transformations": ["..."],
     "target_table": "silver_<name>", "dq_rules": ["..."]}
  ]
}
