from typing import Literal, Sequence

from pulumi import Input, Output, ResourceOptions
from pulumi.dynamic import (
    CheckFailure,
    CheckResult,
    CreateResult,
    DiffResult,
    Resource,
    ResourceProvider,
    UpdateResult,
    ReadResult,
)
from pydantic import BaseModel, ValidationError, validator, Field

from .client import query


class EnvironmentVariableArgs(BaseModel):
    key: str
    value: str
    type: Literal["system", "secret", "encrypted", "plain", "sensitive"]
    target: Sequence[str] = Field(default_factory=lambda: ["production", "preview"])
    # Metadata
    teamId: str
    projectId: str
    apiToken: str

    @validator("type")
    def type_must_be_valid(cls, v):
        if v == "system":
            raise ValueError("System environment variables cannot be created")
        if v in ["secret", "sensitive"]:
            # TODO: if type is "secret", we should pass a secretId as value
            # TODO: if type is "sensitive", then the value gets obfuscated
            raise NotImplementedError(
                "Secret environment variables are not yet supported"
            )
        return v


class EnvironmentVariableModel(EnvironmentVariableArgs):
    id: str
    # Auditing
    createdAt: int
    createdBy: str
    updatedAt: int
    updatedBy: str


class EnvironmentVariableProvider(ResourceProvider):
    def check(self, _olds: dict, news: dict) -> CheckResult:
        """
        Check validates that the given property bag is valid for a resource of the given
        type.
        """
        try:
            EnvironmentVariableArgs.parse_obj(news)
        except ValidationError as e:
            failures = [
                CheckFailure(property=e["loc"][0], reason=e["msg"]) for e in e.errors()
            ]
            return CheckResult(news, failures)
        return super().check(_olds, news)

    def create(self, inputs: dict):
        """
        Create allocates a new instance of the provided resource and returns its unique
        ID afterwards. If this call fails, the resource must not have been created
        (i.e., it is "transactional").
        """
        args = EnvironmentVariableArgs.parse_obj(inputs)

        response_data = query(
            route=f"v10/projects/{args.projectId}/env",
            method="POST",
            api_token=args.apiToken,
            query_parameters={"teamId": args.teamId},
            body_parameters={
                "key": args.key,
                "value": args.value,
                "type": args.type,
                "target": args.target,
            },
        )

        model = EnvironmentVariableModel.parse_obj(response_data["created"])

        return CreateResult(
            id_=response_data["created"]["id"],
            outs=model.dict(),
        )

    def read(self, resource_id, inputs):
        """
        Reads the current live state associated with a resource.  Enough state must be
        included in the inputs to uniquely identify the resource; this is typically just
        the resource ID, but it may also include some properties.
        """
        project_id = inputs["projectId"]
        response_data = query(
            route=f"v9/projects/{project_id}/env/{resource_id}",
            method="GET",
            api_token=inputs["apiToken"],
            query_parameters={"teamId": inputs["teamId"]},
        )

        model = EnvironmentVariableModel(**response_data)

        return ReadResult(id_=resource_id, outs=model.dict())

    def diff(self, resource_id, old_inputs, new_inputs):
        """
        Diff checks what impacts a hypothetical update will have on the resource's
        properties.
        """
        replaces = [
            key for key in ["teamId", "projectId"] if old_inputs[key] != new_inputs[key]
        ]
        delete_before_replace = False
        if not replaces and old_inputs["key"] != new_inputs["key"]:
            replaces.append("key")
            delete_before_replace = True
        olds = EnvironmentVariableArgs.construct(**old_inputs)
        news = EnvironmentVariableArgs.construct(**new_inputs)
        print(olds, news)
        return DiffResult(
            changes=olds != news,
            replaces=replaces,
            delete_before_replace=delete_before_replace,
        )

    def update(self, resource_id, old_inputs, new_inputs):
        """
        Update updates an existing resource with new values.
        """
        project_id = new_inputs["projectId"]
        response_data = query(
            route=f"v9/projects/{project_id}/env/{resource_id}",
            method="PATCH",
            api_token=new_inputs["apiToken"],
            query_parameters={"teamId": new_inputs["teamId"]},
            body_parameters={
                "key": new_inputs["key"],
                "value": new_inputs["value"],
                "type": new_inputs["type"],
                "target": new_inputs["target"],
            },
        )
        return UpdateResult(outs={**new_inputs, **response_data})

    def delete(self, resource_id, inputs):
        """
        Delete tears down an existing resource with the given ID.  If it fails, the
        resource is assumed to still exist.
        """
        project_id = inputs["projectId"]
        query(
            route=f"v9/projects/{project_id}/env/{resource_id}",
            method="DELETE",
            api_token=inputs["apiToken"],
            query_parameters={"teamId": inputs["teamId"]},
            body_parameters={
                "key": inputs["key"],
                "value": inputs["value"],
                "type": inputs["type"],
                "target": inputs["target"],
            },
        )


class EnvironmentVariable(Resource, module="vercel", name="EnvironmentVariable"):
    api_token: Output[str]
    team_id: Output[str]
    project_id: Output[str]

    key: Output[str]
    value: Output[str]
    type_: Output[Literal["system", "secret", "encrypted", "plain", "sensitive"]]

    def __init__(
        self,
        resource_name: str,
        team_id: Input[str],
        project_id: Input[str],
        key: Input[str],
        value: Input[str],
        api_token: Input[str],
        type_: Input[Literal["secret", "encrypted", "plain", "sensitive"]] = "plain",
        target: Input[Sequence[Input[str]]] | None = None,
        opts: ResourceOptions | None = None,
    ):
        super().__init__(
            EnvironmentVariableProvider(),
            resource_name,
            {
                "apiToken": api_token,
                "teamId": team_id,
                "projectId": project_id,
                "key": key,
                "value": value,
                "type": type_,
                "target": target or ["production", "preview"],
            },
            opts,
        )
