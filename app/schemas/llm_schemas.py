"""Pydantic V2 schemas for LLM output - actionable administrative strategies.

These schemas enforce strict JSON structure for the generated action plans,
ensuring compatibility with Phase 4 Next.js frontend visualization.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class UrgencyLevel(str, Enum):
    """Urgency levels for departmental tasks."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ComplianceAssessment(BaseModel):
    """Compliance assessment with strategic recommendation."""
    recommendation: str = Field(
        ...,
        description="Recommended compliance action or strategy",
        min_length=10,
        max_length=500,
    )
    reasoning: str = Field(
        ...,
        description="Detailed reasoning for the recommendation",
        min_length=20,
        max_length=1000,
    )


class LitigationROI(BaseModel):
    """Financial impact analysis for litigation vs. compliance."""
    estimated_compliance_cost: float = Field(
        ...,
        ge=0,
        description="Estimated cost in Indian Rupees to achieve full compliance",
    )
    estimated_litigation_cost: float = Field(
        ...,
        ge=0,
        description="Estimated cost in Indian Rupees if litigated to completion",
    )
    financial_recommendation: str = Field(
        ...,
        description="Cost-benefit recommendation: prioritize compliance or litigation",
        min_length=20,
        max_length=500,
    )


class StatutoryTimeline(BaseModel):
    """Statutory deadlines and limitation periods."""
    explicit_deadline: str = Field(
        ...,
        description="Explicit statutory deadline from the judgment or applicable act",
        min_length=5,
        max_length=300,
    )
    limitation_act_inference: str = Field(
        ...,
        description="Inferred deadline from Limitation Act and related provisions",
        min_length=5,
        max_length=300,
    )


class ActionableDirective(BaseModel):
    """A single actionable task for a department."""
    department_name: str = Field(
        ...,
        description="Name of responsible department (e.g., 'Finance', 'Legal', 'Operations')",
        min_length=3,
        max_length=100,
    )
    task_description: str = Field(
        ...,
        description="Specific, actionable task to be executed",
        min_length=10,
        max_length=500,
    )
    urgency_level: UrgencyLevel = Field(
        ...,
        description="Priority level: HIGH, MEDIUM, LOW",
    )


class ActionPlanResponse(BaseModel):
    """Master schema containing complete administrative action plan."""
    compliance_assessment: ComplianceAssessment = Field(
        ...,
        description="Strategic compliance assessment",
    )
    litigation_roi: LitigationROI = Field(
        ...,
        description="Financial cost-benefit analysis",
    )
    statutory_timeline: StatutoryTimeline = Field(
        ...,
        description="Deadline and limitation period analysis",
    )
    action_directives: List[ActionableDirective] = Field(
        ...,
        min_items=1,
        max_items=20,
        description="List of actionable departmental directives",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "compliance_assessment": {
                    "recommendation": "Establish compliance framework within 90 days",
                    "reasoning": "Early compliance prevents future penalties",
                },
                "litigation_roi": {
                    "estimated_compliance_cost": 500000,
                    "estimated_litigation_cost": 2000000,
                    "financial_recommendation": "Prioritize compliance to avoid escalated litigation costs",
                },
                "statutory_timeline": {
                    "explicit_deadline": "90 days from judgment date",
                    "limitation_act_inference": "3 years from judgment for related claims",
                },
                "action_directives": [
                    {
                        "department_name": "Compliance",
                        "task_description": "Prepare compliance report and submit to regulatory body",
                        "urgency_level": "HIGH",
                    },
                    {
                        "department_name": "Finance",
                        "task_description": "Allocate budget for compliance infrastructure",
                        "urgency_level": "HIGH",
                    },
                ],
            }
        }
