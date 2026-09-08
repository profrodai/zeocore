"""Fail closed on provider workflows outside the supported linear drip subset."""

from __future__ import annotations

from typing import Any

from .models import EmailSequence, SequenceStep


def validate_workflow(data: dict[str, Any]) -> EmailSequence:
    """Validate retrieved definitions, including every action, edge and trigger.

    Deliberately accepts only compiler-shaped workflows. Unknown behavior is
    refused, not silently discarded by a replacement PUT.
    """
    # Documented optional behavior fields with null values express absence.
    # Empty objects are NOT assumed inert: an unrecognized trigger fails closed.
    data = _without_null_decorations(data)
    if (
        data.get("type") != "CONTACT_FLOW"
        or data.get("objectTypeId") != "0-1"
        or data.get("flowType") != "WORKFLOW"
    ):
        raise ValueError("Only contact-based marketing workflows are supported")
    actions = data.get("actions")
    if not isinstance(actions, list) or not 1 <= len(actions) <= 100:
        raise ValueError("Workflow must have a bounded marketing email graph")
    steps = _parse_steps(actions)
    sequence = EmailSequence(
        name=data.get("name", ""),
        steps=tuple(steps),
        suppression_list_ids=data.get("suppressionListIds", ()),
    )
    if type(data.get("isEnabled")) is not bool:
        raise ValueError("Workflow enabled state is missing")
    expected_flow = sequence.to_api(enabled=data["isEnabled"])
    metadata = {
        "id",
        "revisionId",
        "createdAt",
        "updatedAt",
        "nextAvailableActionId",
        "crmObjectCreationStatus",
        "description",
        "uuid",
    }
    if set(data) - set(expected_flow) - metadata:
        raise ValueError("Workflow has unsupported triggers or settings")
    if any(data.get(key) != value for key, value in expected_flow.items()):
        raise ValueError(
            "Workflow enrollment, suppression or definition is unsupported"
        )
    if data.get("canEnrollFromSalesforce") is not False:
        raise ValueError("Salesforce enrollment is unsupported")
    criteria = data.get("enrollmentCriteria", {})
    if criteria.get("shouldReEnroll") is not False:
        raise ValueError("Re-enrollment is unsupported")
    return sequence


def _without_null_decorations(data: dict[str, Any]) -> dict[str, Any]:
    optional = {
        "enrollmentSchedule",
        "eventAnchor",
        "goalFilterBranch",
        "unEnrollmentSetting",
    }
    result = {
        key: value
        for key, value in data.items()
        if key not in optional or value is not None
    }
    actions = result.get("actions")
    if isinstance(actions, list) and all(
        isinstance(action, dict) for action in actions
    ):
        result["actions"] = [
            {key: value for key, value in action.items() if value is not None}
            for action in actions
        ]
    return result


def _parse_steps(actions: list[dict[str, Any]]) -> list[SequenceStep]:
    steps: list[SequenceStep] = []
    delay = 0
    for index, action in enumerate(actions, 1):
        if not isinstance(action, dict) or action.get("actionTypeId") not in {
            "0-1",
            "0-4",
        }:
            raise ValueError(
                "Workflow contains actions outside marketing email and delay"
            )
        fields = action.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("Workflow action fields are invalid")
        expected: dict[str, Any] = {
            "actionTypeId": action["actionTypeId"],
            "fields": fields,
            "type": "SINGLE_CONNECTION",
            "actionId": str(index),
            "actionTypeVersion": 0,
        }
        if index < len(actions):
            expected["connection"] = {
                "edgeType": "STANDARD",
                "nextActionId": str(index + 1),
            }
        if action != expected or type(action.get("actionTypeVersion")) is not int:
            raise ValueError(
                "Unsupported workflow action version, branch or graph edge"
            )
        if action["actionTypeId"] == "0-1":
            value = fields.get("delta")
            if (
                delay
                or set(fields) != {"delta", "time_unit"}
                or fields.get("time_unit") != "MINUTES"
                or not isinstance(value, str)
                or not value.isascii()
                or not value.isdigit()
                or len(value) > 6
                or not 1 <= int(value) <= 525600
            ):
                raise ValueError("Unsupported workflow delay")
            delay = int(value)
        else:
            if set(fields) != {"content_id"}:
                raise ValueError("Unsupported marketing email fields")
            steps.append(
                SequenceStep(email_id=fields["content_id"], delay_minutes=delay)
            )
            delay = 0
    if delay:
        raise ValueError("Workflow cannot end in a dangling delay")
    return steps
