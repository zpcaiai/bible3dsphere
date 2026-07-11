from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from mission_os.religious_freedom import validate_program_policy

class ProgramStep(BaseModel):
    key:str=Field(min_length=2,max_length=80); title:str=Field(min_length=2,max_length=160)
    stepType:Literal['required','optional','conditional','synchronous','asynchronous']='required'
    required:bool=True; condition:dict|None=None; contentRefs:list[str]=Field(default_factory=list,max_length=50)

class ProgramPathway(BaseModel):
    key:str=Field(min_length=2,max_length=80); title:str=Field(min_length=2,max_length=160)
    eligibility:dict=Field(default_factory=dict); steps:list[ProgramStep]=Field(min_length=1,max_length=100)

class ProgramDefinition(BaseModel):
    id:str=Field(min_length=3,max_length=80); version:str=Field(pattern=r'^\d+\.\d+\.\d+$')
    groupType:str=Field(min_length=2,max_length=80); title:str=Field(min_length=3,max_length=160); description:str=Field(min_length=10,max_length=2000)
    consentRequirements:list[str]=Field(min_length=1); safeguardingProfile:dict
    durationWeeks:int=Field(ge=1,le=104); cadence:str=Field(min_length=2,max_length=80)
    sessionMode:Literal['online','offline','hybrid','async']; pathways:list[ProgramPathway]=Field(min_length=1,max_length=20)
    riskTriggers:list[str]=Field(min_length=1); referralTypes:list[str]=Field(default_factory=list); outcomeMetrics:list[str]=Field(min_length=1)
    @model_validator(mode='after')
    def safety_required(self):
        if not self.safeguardingProfile.get('noCoercion') or not self.safeguardingProfile.get('professionalReferral'):
            raise ValueError('Safeguarding must require noCoercion and professionalReferral')
        return self

def validate_for_publish(payload:dict)->ProgramDefinition:
    validate_program_policy(payload)
    return ProgramDefinition.model_validate(payload)
