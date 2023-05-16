"""A Python Pulumi program"""
import pulumi
import pulumi_vercel as vercel

vercel_config = pulumi.Config("vercel")

env = vercel.EnvironmentVariable(
    "bar",
    key="BAR",
    value="qux",
    type_="plain",
    project_id="app",
    team_id="safebear",
    api_token=vercel_config.require_secret("token"),
)
