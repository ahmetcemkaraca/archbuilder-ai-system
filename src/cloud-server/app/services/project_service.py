"""
Project Service Implementation for ArchBuilder.AI
Handles project management, workflow orchestration, progress tracking,
and step-by-step execution coordination for architectural design automation
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import structlog

from app.models.projects import (
    Project,
    ProjectRequest,
    ProjectStep,
    ProjectStepStatus,
    ProjectStatus,
    LayoutGeneration,
    StepValidation,
    ProjectMetrics,
    WorkflowTemplate
)
from app.models.ai import AILayoutRequest, AILayoutResponse
from app.models.documents import DocumentProcessingResult
from app.services.ai_service import AIService
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.core.exceptions import (
    ProjectServiceException,
    WorkflowException,
    ValidationException
)
from app.core.config import settings
from app.utils.cache import AsyncCache
from app.utils.performance import PerformanceTracker
from app.core.logging import get_logger, log_ai_operation

logger = structlog.get_logger(__name__)


class WorkflowStepType(str, Enum):
    """Types of workflow steps"""
    DOCUMENT_PROCESSING = "document_processing"
    RAG_INDEXING = "rag_indexing"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    SITE_ANALYSIS = "site_analysis"
    LAYOUT_GENERATION = "layout_generation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    REVIT_PREPARATION = "revit_preparation"
    FINAL_REVIEW = "final_review"


class ProjectWorkflowOrchestrator:
    """Orchestrates project workflows with step-by-step execution"""
    
    def __init__(
        self,
        ai_service: AIService,
        document_service: DocumentService,
        rag_service: RAGService,
        cache: Optional[AsyncCache] = None
    ):
        self.ai_service = ai_service
        self.document_service = document_service
        self.rag_service = rag_service
        self.cache = cache
        self.logger = get_logger(__name__)
        
        # Workflow templates by project complexity
        self.workflow_templates = {
            "simple": self._create_simple_workflow_template(),
            "standard": self._create_standard_workflow_template(),
            "complex": self._create_complex_workflow_template()
        }
    
    def _create_simple_workflow_template(self) -> List[Dict[str, Any]]:
        """Create workflow template for simple projects (5-15 steps)"""
        
        return [
            {
                "step_type": WorkflowStepType.DOCUMENT_PROCESSING,
                "name": "Process uploaded documents",
                "description": "Extract text and data from uploaded documents",
                "estimated_duration_minutes": 5,
                "dependencies": [],
                "validation_criteria": ["documents_processed", "text_extracted"]
            },
            {
                "step_type": WorkflowStepType.RAG_INDEXING,
                "name": "Index documents for knowledge retrieval",
                "description": "Create searchable index from document content",
                "estimated_duration_minutes": 3,
                "dependencies": ["document_processing"],
                "validation_criteria": ["documents_indexed", "embeddings_created"]
            },
            {
                "step_type": WorkflowStepType.REQUIREMENT_ANALYSIS,
                "name": "Analyze project requirements",
                "description": "Extract and validate project requirements from user input",
                "estimated_duration_minutes": 5,
                "dependencies": ["rag_indexing"],
                "validation_criteria": ["requirements_extracted", "regulations_identified"]
            },
            {
                "step_type": WorkflowStepType.SITE_ANALYSIS,
                "name": "Analyze site conditions",
                "description": "Process site data and constraints",
                "estimated_duration_minutes": 7,
                "dependencies": ["requirement_analysis"],
                "validation_criteria": ["site_constraints_analyzed", "zoning_checked"]
            },
            {
                "step_type": WorkflowStepType.LAYOUT_GENERATION,
                "name": "Generate initial layout",
                "description": "Create basic architectural layout using AI",
                "estimated_duration_minutes": 15,
                "dependencies": ["site_analysis"],
                "validation_criteria": ["layout_generated", "rooms_placed", "circulation_designed"]
            },
            {
                "step_type": WorkflowStepType.VALIDATION,
                "name": "Validate against building codes",
                "description": "Check layout compliance with regulations",
                "estimated_duration_minutes": 8,
                "dependencies": ["layout_generation"],
                "validation_criteria": ["code_compliance_checked", "safety_validated"]
            },
            {
                "step_type": WorkflowStepType.OPTIMIZATION,
                "name": "Optimize layout efficiency",
                "description": "Improve space utilization and flow",
                "estimated_duration_minutes": 10,
                "dependencies": ["validation"],
                "validation_criteria": ["efficiency_optimized", "flow_improved"]
            },
            {
                "step_type": WorkflowStepType.REVIT_PREPARATION,
                "name": "Prepare Revit commands",
                "description": "Generate executable Revit API commands",
                "estimated_duration_minutes": 12,
                "dependencies": ["optimization"],
                "validation_criteria": ["revit_commands_generated", "families_selected"]
            },
            {
                "step_type": WorkflowStepType.FINAL_REVIEW,
                "name": "Final quality review",
                "description": "Comprehensive review of generated design",
                "estimated_duration_minutes": 5,
                "dependencies": ["revit_preparation"],
                "validation_criteria": ["quality_checked", "completeness_verified"]
            }
        ]
    
    def _create_standard_workflow_template(self) -> List[Dict[str, Any]]:
        """Create workflow template for standard projects (15-35 steps)"""
        
        simple_steps = self._create_simple_workflow_template()
        
        # Add additional steps for standard complexity
        additional_steps = [
            {
                "step_type": WorkflowStepType.LAYOUT_GENERATION,
                "name": "Generate floor plan alternatives",
                "description": "Create multiple layout options for comparison",
                "estimated_duration_minutes": 20,
                "dependencies": ["layout_generation"],
                "validation_criteria": ["alternatives_generated", "options_compared"]
            },
            {
                "step_type": WorkflowStepType.OPTIMIZATION,
                "name": "Environmental analysis",
                "description": "Analyze lighting, ventilation, and energy efficiency",
                "estimated_duration_minutes": 15,
                "dependencies": ["layout_generation"],
                "validation_criteria": ["environmental_analyzed", "efficiency_calculated"]
            },
            {
                "step_type": WorkflowStepType.VALIDATION,
                "name": "Structural feasibility check",
                "description": "Validate structural requirements and constraints",
                "estimated_duration_minutes": 12,
                "dependencies": ["optimization"],
                "validation_criteria": ["structure_validated", "loads_calculated"]
            },
            {
                "step_type": WorkflowStepType.OPTIMIZATION,
                "name": "Cost optimization",
                "description": "Optimize design for construction cost efficiency",
                "estimated_duration_minutes": 18,
                "dependencies": ["validation"],
                "validation_criteria": ["cost_optimized", "materials_selected"]
            }
        ]
        
        # Insert additional steps into workflow
        workflow = simple_steps.copy()
        
        # Insert alternatives generation after initial layout
        layout_index = next(i for i, step in enumerate(workflow) if step["step_type"] == WorkflowStepType.LAYOUT_GENERATION)
        workflow.insert(layout_index + 1, additional_steps[0])
        
        # Insert environmental analysis
        workflow.insert(layout_index + 2, additional_steps[1])
        
        # Insert structural check
        workflow.insert(layout_index + 3, additional_steps[2])
        
        # Insert cost optimization
        workflow.insert(layout_index + 4, additional_steps[3])
        
        # Update dependencies for subsequent steps
        for i, step in enumerate(workflow):
            if i > layout_index + 4:
                step["dependencies"] = ["cost_optimization"]
        
        return workflow
    
    def _create_complex_workflow_template(self) -> List[Dict[str, Any]]:
        """Create workflow template for complex projects (35-50 steps)"""
        
        standard_steps = self._create_standard_workflow_template()
        
        # Add comprehensive steps for complex projects
        complex_additions = [
            {
                "step_type": WorkflowStepType.SITE_ANALYSIS,
                "name": "Geotechnical analysis",
                "description": "Analyze soil conditions and foundation requirements",
                "estimated_duration_minutes": 25,
                "dependencies": ["site_analysis"],
                "validation_criteria": ["geotechnical_analyzed", "foundation_designed"]
            },
            {
                "step_type": WorkflowStepType.LAYOUT_GENERATION,
                "name": "Multi-story coordination",
                "description": "Coordinate layout across multiple floors",
                "estimated_duration_minutes": 30,
                "dependencies": ["layout_generation"],
                "validation_criteria": ["floors_coordinated", "vertical_circulation_designed"]
            },
            {
                "step_type": WorkflowStepType.VALIDATION,
                "name": "MEP systems integration",
                "description": "Integrate mechanical, electrical, and plumbing systems",
                "estimated_duration_minutes": 35,
                "dependencies": ["layout_generation"],
                "validation_criteria": ["mep_integrated", "systems_coordinated"]
            },
            {
                "step_type": WorkflowStepType.OPTIMIZATION,
                "name": "Sustainability optimization",
                "description": "Optimize for LEED/BREEAM certification requirements",
                "estimated_duration_minutes": 40,
                "dependencies": ["optimization"],
                "validation_criteria": ["sustainability_optimized", "certifications_validated"]
            },
            {
                "step_type": WorkflowStepType.VALIDATION,
                "name": "Accessibility compliance",
                "description": "Ensure ADA/accessibility compliance",
                "estimated_duration_minutes": 20,
                "dependencies": ["optimization"],
                "validation_criteria": ["accessibility_validated", "ada_compliant"]
            },
            {
                "step_type": WorkflowStepType.OPTIMIZATION,
                "name": "Construction sequencing",
                "description": "Optimize construction phases and logistics",
                "estimated_duration_minutes": 30,
                "dependencies": ["optimization"],
                "validation_criteria": ["sequencing_optimized", "logistics_planned"]
            }
        ]
        
        # Integrate complex additions into workflow
        workflow = standard_steps.copy()
        
        # Add complex steps at appropriate points
        for addition in complex_additions:
            # Find appropriate insertion point based on dependencies
            insert_index = len(workflow) - 2  # Before final review
            
            # Find better insertion point based on step type
            for i, step in enumerate(workflow):
                if step["step_type"] == addition["step_type"]:
                    insert_index = i + 1
                    break
            
            workflow.insert(insert_index, addition)
        
        return workflow
    
    async def create_workflow_for_project(
        self,
        project_request: ProjectRequest,
        correlation_id: str
    ) -> List[ProjectStep]:
        """Create customized workflow based on project complexity"""
        
        logger.info(
            "Creating workflow for project",
            project_type=project_request.project_type,
            complexity=project_request.complexity,
            correlation_id=correlation_id
        )
        
        try:
            # Determine complexity level
            complexity = self._determine_project_complexity(project_request)
            
            # Get appropriate template
            template = self.workflow_templates.get(complexity, self.workflow_templates["standard"])
            
            # Create project steps
            steps = []
            total_duration = 0
            
            for i, step_template in enumerate(template):
                step = ProjectStep(
                    step_id=f"step_{i+1:02d}",
                    step_index=i,
                    step_type=step_template["step_type"],
                    name=step_template["name"],
                    description=step_template["description"],
                    status=ProjectStepStatus.PENDING,
                    estimated_duration_minutes=step_template["estimated_duration_minutes"],
                    dependencies=step_template["dependencies"],
                    validation_criteria=step_template["validation_criteria"],
                    created_at=datetime.utcnow()
                )
                
                steps.append(step)
                total_duration += step.estimated_duration_minutes
            
            logger.info(
                "Workflow created successfully",
                complexity=complexity,
                total_steps=len(steps),
                estimated_duration_minutes=total_duration,
                correlation_id=correlation_id
            )
            
            return steps
            
        except Exception as e:
            logger.error(
                "Workflow creation failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise WorkflowException(
                "Failed to create project workflow",
                "WORKFLOW_CREATION_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    def _determine_project_complexity(self, project_request: ProjectRequest) -> str:
        """Determine project complexity based on requirements"""
        
        complexity_score = 0
        
        # Building type complexity
        complex_building_types = ["hospital", "school", "office_complex", "mixed_use", "industrial"]
        if project_request.building_type in complex_building_types:
            complexity_score += 2
        
        # Size complexity
        if project_request.total_area and project_request.total_area > 10000:  # sq ft
            complexity_score += 2
        elif project_request.total_area and project_request.total_area > 5000:
            complexity_score += 1
        
        # Floor count complexity
        if project_request.floors and project_request.floors > 5:
            complexity_score += 2
        elif project_request.floors and project_request.floors > 2:
            complexity_score += 1
        
        # Document complexity
        if len(project_request.uploaded_documents or []) > 10:
            complexity_score += 2
        elif len(project_request.uploaded_documents or []) > 5:
            complexity_score += 1
        
        # Special requirements complexity
        special_requirements = ["sustainability", "accessibility", "historic", "seismic"]
        special_count = sum(1 for req in special_requirements if req in (project_request.special_requirements or []))
        complexity_score += special_count
        
        # Determine complexity level
        if complexity_score >= 8:
            return "complex"
        elif complexity_score >= 4:
            return "standard"
        else:
            return "simple"
    
    async def execute_workflow_step(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Execute a single workflow step"""
        
        logger.info(
            "Executing workflow step",
            project_id=project.project_id,
            step_id=step.step_id,
            step_type=step.step_type,
            correlation_id=correlation_id
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Update step status
            step.status = ProjectStepStatus.IN_PROGRESS
            step.started_at = start_time
            
            # Execute step based on type
            if step.step_type == WorkflowStepType.DOCUMENT_PROCESSING:
                result = await self._execute_document_processing(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.RAG_INDEXING:
                result = await self._execute_rag_indexing(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.REQUIREMENT_ANALYSIS:
                result = await self._execute_requirement_analysis(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.SITE_ANALYSIS:
                result = await self._execute_site_analysis(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.LAYOUT_GENERATION:
                result = await self._execute_layout_generation(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.VALIDATION:
                result = await self._execute_validation(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.OPTIMIZATION:
                result = await self._execute_optimization(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.REVIT_PREPARATION:
                result = await self._execute_revit_preparation(project, step, correlation_id)
            elif step.step_type == WorkflowStepType.FINAL_REVIEW:
                result = await self._execute_final_review(project, step, correlation_id)
            else:
                raise WorkflowException(f"Unknown step type: {step.step_type}")
            
            # Update step completion
            step.completed_at = datetime.utcnow()
            step.actual_duration_minutes = int((step.completed_at - start_time).total_seconds() / 60)
            step.output_data = result
            
            # Validate step completion
            validation_success = await self._validate_step_completion(step, result, correlation_id)
            
            if validation_success:
                step.status = ProjectStepStatus.COMPLETED
                logger.info(
                    "Workflow step completed successfully",
                    project_id=project.project_id,
                    step_id=step.step_id,
                    duration_minutes=step.actual_duration_minutes,
                    correlation_id=correlation_id
                )
                return True, result
            else:
                step.status = ProjectStepStatus.FAILED
                step.error_message = "Step validation failed"
                logger.error(
                    "Workflow step validation failed",
                    project_id=project.project_id,
                    step_id=step.step_id,
                    correlation_id=correlation_id
                )
                return False, {"error": "Step validation failed"}
                
        except Exception as e:
            step.status = ProjectStepStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.actual_duration_minutes = int((step.completed_at - start_time).total_seconds() / 60)
            step.error_message = str(e)
            
            logger.error(
                "Workflow step execution failed",
                project_id=project.project_id,
                step_id=step.step_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            return False, {"error": str(e)}
    
    async def _execute_document_processing(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute document processing step"""
        
        if not project.uploaded_documents:
            return {"message": "No documents to process", "processed_count": 0}
        
        processed_documents = []
        
        for doc_id in project.uploaded_documents:
            try:
                # Process document using document service
                result = await self.document_service.process_document_async(
                    document_id=doc_id,
                    correlation_id=correlation_id
                )
                
                if result and result.success:
                    processed_documents.append({
                        "document_id": doc_id,
                        "status": "success",
                        "extracted_text_length": len(result.extracted_text or ""),
                        "confidence": result.confidence_score
                    })
                else:
                    processed_documents.append({
                        "document_id": doc_id,
                        "status": "failed",
                        "error": result.error_message if result else "Unknown error"
                    })
                    
            except Exception as e:
                processed_documents.append({
                    "document_id": doc_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        successful_count = sum(1 for doc in processed_documents if doc["status"] == "success")
        
        return {
            "processed_documents": processed_documents,
            "processed_count": len(processed_documents),
            "successful_count": successful_count,
            "success_rate": successful_count / len(processed_documents) if processed_documents else 0
        }
    
    async def _execute_rag_indexing(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute RAG indexing step"""
        
        if not project.uploaded_documents:
            return {"message": "No documents to index", "indexed_count": 0}
        
        indexed_documents = []
        
        for doc_id in project.uploaded_documents:
            try:
                # Get processed document content
                doc_content = await self.document_service.get_document_content(doc_id, correlation_id)
                
                if doc_content:
                    # Index document for RAG
                    index_result = await self.rag_service.index_document(
                        document_id=doc_id,
                        content=doc_content.get("extracted_text", ""),
                        metadata=doc_content.get("metadata", {}),
                        correlation_id=correlation_id
                    )
                    
                    indexed_documents.append({
                        "document_id": doc_id,
                        "status": "indexed",
                        "chunk_count": index_result.get("chunk_count", 0)
                    })
                else:
                    indexed_documents.append({
                        "document_id": doc_id,
                        "status": "failed",
                        "error": "No content available"
                    })
                    
            except Exception as e:
                indexed_documents.append({
                    "document_id": doc_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        successful_count = sum(1 for doc in indexed_documents if doc["status"] == "indexed")
        total_chunks = sum(doc.get("chunk_count", 0) for doc in indexed_documents)
        
        return {
            "indexed_documents": indexed_documents,
            "indexed_count": successful_count,
            "total_chunks": total_chunks,
            "success_rate": successful_count / len(indexed_documents) if indexed_documents else 0
        }
    
    async def _execute_requirement_analysis(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute requirement analysis step"""
        
        # Create AI request for requirement analysis
        analysis_request = AILayoutRequest(
            user_input=project.description,
            project_type=project.project_type,
            building_type=project.building_type,
            total_area=project.total_area,
            floors=project.floors,
            requirements=project.requirements or [],
            constraints=project.constraints or [],
            language=project.language,
            correlation_id=correlation_id
        )
        
        # Use AI service to analyze requirements
        analysis_response = await self.ai_service.analyze_project_requirements(
            analysis_request, correlation_id
        )
        
        if analysis_response.success:
            return {
                "requirements_analyzed": True,
                "extracted_requirements": analysis_response.layout_data.get("requirements", []),
                "identified_regulations": analysis_response.layout_data.get("regulations", []),
                "compliance_notes": analysis_response.layout_data.get("compliance_notes", []),
                "confidence": analysis_response.confidence_score
            }
        else:
            raise WorkflowException(f"Requirement analysis failed: {analysis_response.error_message}")
    
    async def _execute_site_analysis(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute site analysis step"""
        
        # Analyze site conditions using AI
        site_request = AILayoutRequest(
            user_input=f"Analyze site conditions for {project.building_type}",
            project_type=project.project_type,
            building_type=project.building_type,
            site_area=project.site_area,
            site_constraints=project.site_constraints or [],
            language=project.language,
            correlation_id=correlation_id
        )
        
        site_response = await self.ai_service.analyze_site_conditions(
            site_request, correlation_id
        )
        
        if site_response.success:
            return {
                "site_analyzed": True,
                "site_constraints": site_response.layout_data.get("constraints", []),
                "zoning_requirements": site_response.layout_data.get("zoning", []),
                "environmental_factors": site_response.layout_data.get("environmental", []),
                "recommendations": site_response.layout_data.get("recommendations", []),
                "confidence": site_response.confidence_score
            }
        else:
            raise WorkflowException(f"Site analysis failed: {site_response.error_message}")
    
    async def _execute_layout_generation(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute layout generation step"""
        
        # Create comprehensive layout request
        layout_request = AILayoutRequest(
            user_input=project.description,
            project_type=project.project_type,
            building_type=project.building_type,
            total_area=project.total_area,
            floors=project.floors,
            requirements=project.requirements or [],
            constraints=project.constraints or [],
            site_constraints=project.site_constraints or [],
            language=project.language,
            correlation_id=correlation_id
        )
        
        # Generate layout using AI service
        layout_response = await self.ai_service.generate_architectural_layout(
            layout_request, correlation_id
        )
        
        if layout_response.success:
            return {
                "layout_generated": True,
                "rooms": layout_response.layout_data.get("rooms", []),
                "circulation": layout_response.layout_data.get("circulation", {}),
                "structural_elements": layout_response.layout_data.get("structure", []),
                "dimensions": layout_response.layout_data.get("dimensions", {}),
                "revit_commands": layout_response.revit_commands,
                "confidence": layout_response.confidence_score
            }
        else:
            raise WorkflowException(f"Layout generation failed: {layout_response.error_message}")
    
    async def _execute_validation(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute validation step"""
        
        # Get current layout data from previous steps
        layout_data = self._get_project_layout_data(project)
        
        # Validate against building codes using AI
        validation_request = AILayoutRequest(
            user_input=f"Validate layout against building codes",
            project_type=project.project_type,
            building_type=project.building_type,
            layout_data=layout_data,
            language=project.language,
            correlation_id=correlation_id
        )
        
        validation_response = await self.ai_service.validate_layout_compliance(
            validation_request, correlation_id
        )
        
        if validation_response.success:
            return {
                "validation_complete": True,
                "compliance_status": validation_response.layout_data.get("compliance", "unknown"),
                "violations": validation_response.layout_data.get("violations", []),
                "recommendations": validation_response.layout_data.get("recommendations", []),
                "safety_checks": validation_response.layout_data.get("safety", []),
                "confidence": validation_response.confidence_score
            }
        else:
            raise WorkflowException(f"Validation failed: {validation_response.error_message}")
    
    async def _execute_optimization(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute optimization step"""
        
        # Get current layout data
        layout_data = self._get_project_layout_data(project)
        
        # Optimize layout using AI
        optimization_request = AILayoutRequest(
            user_input=f"Optimize layout for efficiency and compliance",
            project_type=project.project_type,
            building_type=project.building_type,
            layout_data=layout_data,
            language=project.language,
            correlation_id=correlation_id
        )
        
        optimization_response = await self.ai_service.optimize_layout(
            optimization_request, correlation_id
        )
        
        if optimization_response.success:
            return {
                "optimization_complete": True,
                "efficiency_improvements": optimization_response.layout_data.get("improvements", []),
                "space_utilization": optimization_response.layout_data.get("utilization", {}),
                "cost_savings": optimization_response.layout_data.get("savings", {}),
                "optimized_layout": optimization_response.layout_data,
                "confidence": optimization_response.confidence_score
            }
        else:
            raise WorkflowException(f"Optimization failed: {optimization_response.error_message}")
    
    async def _execute_revit_preparation(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute Revit preparation step"""
        
        # Get finalized layout data
        layout_data = self._get_project_layout_data(project)
        
        # Generate Revit commands using AI
        revit_request = AILayoutRequest(
            user_input="Generate Revit API commands for layout implementation",
            project_type=project.project_type,
            building_type=project.building_type,
            layout_data=layout_data,
            language=project.language,
            correlation_id=correlation_id
        )
        
        revit_response = await self.ai_service.generate_revit_commands(
            revit_request, correlation_id
        )
        
        if revit_response.success:
            return {
                "revit_commands_generated": True,
                "commands": revit_response.revit_commands,
                "families": revit_response.layout_data.get("families", []),
                "materials": revit_response.layout_data.get("materials", []),
                "parameters": revit_response.layout_data.get("parameters", {}),
                "confidence": revit_response.confidence_score
            }
        else:
            raise WorkflowException(f"Revit preparation failed: {revit_response.error_message}")
    
    async def _execute_final_review(
        self,
        project: Project,
        step: ProjectStep,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Execute final review step"""
        
        # Collect all project data for comprehensive review
        project_summary = {
            "project_id": project.project_id,
            "project_type": project.project_type,
            "building_type": project.building_type,
            "total_area": project.total_area,
            "floors": project.floors,
            "workflow_steps": len(project.workflow_steps),
            "completed_steps": len([s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED])
        }
        
        # Perform final quality check
        quality_score = self._calculate_project_quality_score(project)
        
        return {
            "final_review_complete": True,
            "project_summary": project_summary,
            "quality_score": quality_score,
            "completeness": self._calculate_project_completeness(project),
            "recommendations": self._generate_final_recommendations(project),
            "ready_for_revit": quality_score >= 0.8
        }
    
    def _get_project_layout_data(self, project: Project) -> Dict[str, Any]:
        """Extract layout data from completed project steps"""
        
        layout_data = {}
        
        for step in project.workflow_steps:
            if step.status == ProjectStepStatus.COMPLETED and step.output_data:
                if step.step_type == WorkflowStepType.LAYOUT_GENERATION:
                    layout_data.update(step.output_data)
                elif step.step_type == WorkflowStepType.OPTIMIZATION:
                    layout_data.update(step.output_data.get("optimized_layout", {}))
        
        return layout_data
    
    def _calculate_project_quality_score(self, project: Project) -> float:
        """Calculate overall project quality score"""
        
        if not project.workflow_steps:
            return 0.0
        
        completed_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED]
        completion_rate = len(completed_steps) / len(project.workflow_steps)
        
        # Average confidence scores
        confidence_scores = []
        for step in completed_steps:
            if step.output_data and "confidence" in step.output_data:
                confidence_scores.append(step.output_data["confidence"])
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        # Calculate quality score
        quality_score = (completion_rate * 0.6) + (avg_confidence * 0.4)
        
        return round(quality_score, 2)
    
    def _calculate_project_completeness(self, project: Project) -> float:
        """Calculate project completeness percentage"""
        
        if not project.workflow_steps:
            return 0.0
        
        completed_count = len([s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED])
        total_count = len(project.workflow_steps)
        
        return round((completed_count / total_count) * 100, 1)
    
    def _generate_final_recommendations(self, project: Project) -> List[str]:
        """Generate final recommendations based on project analysis"""
        
        recommendations = []
        
        # Check project completeness
        completeness = self._calculate_project_completeness(project)
        if completeness < 100:
            recommendations.append(f"Project is {completeness}% complete. Consider completing remaining steps.")
        
        # Check for failed steps
        failed_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.FAILED]
        if failed_steps:
            recommendations.append(f"Review and retry {len(failed_steps)} failed workflow steps.")
        
        # Check quality score
        quality_score = self._calculate_project_quality_score(project)
        if quality_score < 0.7:
            recommendations.append("Consider reviewing and improving design quality before Revit implementation.")
        
        if not recommendations:
            recommendations.append("Project is ready for Revit implementation.")
        
        return recommendations
    
    async def _validate_step_completion(
        self,
        step: ProjectStep,
        result: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """Validate that a step has been completed successfully"""
        
        try:
            if not step.validation_criteria:
                return True  # No specific criteria to validate
            
            validation_results = []
            
            for criterion in step.validation_criteria:
                if criterion in result:
                    validation_results.append(True)
                elif criterion.endswith("_generated") and any(key.endswith("_generated") for key in result.keys()):
                    validation_results.append(True)
                elif criterion.endswith("_analyzed") and any(key.endswith("_analyzed") for key in result.keys()):
                    validation_results.append(True)
                else:
                    validation_results.append(False)
            
            # Require at least 70% of criteria to be met
            success_rate = sum(validation_results) / len(validation_results)
            return success_rate >= 0.7
            
        except Exception as e:
            logger.error(
                "Step validation error",
                step_id=step.step_id,
                error=str(e),
                correlation_id=correlation_id
            )
            return False


class ProjectService:
    """Main project service for managing architectural design projects"""
    
    def __init__(
        self,
        ai_service: AIService,
        document_service: DocumentService,
        rag_service: RAGService,
        cache: Optional[AsyncCache] = None,
        performance_tracker: Optional[PerformanceTracker] = None
    ):
        self.ai_service = ai_service
        self.document_service = document_service
        self.rag_service = rag_service
        self.cache = cache
        self.performance_tracker = performance_tracker
        self.logger = get_logger(__name__)
        
        # Initialize workflow orchestrator
        self.workflow_orchestrator = ProjectWorkflowOrchestrator(
            ai_service, document_service, rag_service, cache
        )
        
        # Project storage (in production, this would be a database)
        self.projects: Dict[str, Project] = {}
        
        logger.info("Project Service initialized")
    
    async def create_project(
        self,
        project_request: ProjectRequest,
        correlation_id: str
    ) -> Project:
        """Create a new architectural design project"""
        
        logger.info(
            "Creating new project",
            project_type=project_request.project_type,
            building_type=project_request.building_type,
            correlation_id=correlation_id
        )
        
        try:
            # Generate project ID
            project_id = f"proj_{uuid.uuid4().hex[:8]}"
            
            # Create workflow steps
            workflow_steps = await self.workflow_orchestrator.create_workflow_for_project(
                project_request, correlation_id
            )
            
            # Calculate estimated duration
            estimated_duration = sum(step.estimated_duration_minutes for step in workflow_steps)
            
            # Create project
            project = Project(
                project_id=project_id,
                name=project_request.name,
                description=project_request.description,
                project_type=project_request.project_type,
                building_type=project_request.building_type,
                total_area=project_request.total_area,
                floors=project_request.floors,
                site_area=project_request.site_area,
                requirements=project_request.requirements,
                constraints=project_request.constraints,
                site_constraints=project_request.site_constraints,
                uploaded_documents=project_request.uploaded_documents,
                language=project_request.language,
                status=ProjectStatus.CREATED,
                workflow_steps=workflow_steps,
                estimated_duration_minutes=estimated_duration,
                created_at=datetime.utcnow(),
                correlation_id=correlation_id
            )
            
            # Store project
            self.projects[project_id] = project
            
            logger.info(
                "Project created successfully",
                project_id=project_id,
                workflow_steps=len(workflow_steps),
                estimated_duration_minutes=estimated_duration,
                correlation_id=correlation_id
            )
            
            return project
            
        except Exception as e:
            logger.error(
                "Project creation failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise ProjectServiceException(
                "Failed to create project",
                "PROJECT_CREATION_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    async def execute_project_workflow(
        self,
        project_id: str,
        correlation_id: str
    ) -> Project:
        """Execute the complete project workflow"""
        
        logger.info(
            "Starting project workflow execution",
            project_id=project_id,
            correlation_id=correlation_id
        )
        
        try:
            project = self.projects.get(project_id)
            if not project:
                raise ProjectServiceException(f"Project {project_id} not found")
            
            # Update project status
            project.status = ProjectStatus.IN_PROGRESS
            project.started_at = datetime.utcnow()
            
            # Execute workflow steps
            for step in project.workflow_steps:
                # Check dependencies
                if not self._are_dependencies_completed(step, project.workflow_steps):
                    logger.warning(
                        "Step dependencies not met, skipping",
                        project_id=project_id,
                        step_id=step.step_id,
                        correlation_id=correlation_id
                    )
                    continue
                
                # Execute step
                success, result = await self.workflow_orchestrator.execute_workflow_step(
                    project, step, correlation_id
                )
                
                if not success:
                    logger.error(
                        "Workflow step failed, stopping execution",
                        project_id=project_id,
                        step_id=step.step_id,
                        error=result.get("error"),
                        correlation_id=correlation_id
                    )
                    project.status = ProjectStatus.FAILED
                    break
            
            # Update project completion
            if project.status != ProjectStatus.FAILED:
                completed_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED]
                if len(completed_steps) == len(project.workflow_steps):
                    project.status = ProjectStatus.COMPLETED
                    project.completed_at = datetime.utcnow()
                    project.actual_duration_minutes = int(
                        (project.completed_at - project.started_at).total_seconds() / 60
                    )
                else:
                    project.status = ProjectStatus.PARTIALLY_COMPLETED
            
            logger.info(
                "Project workflow execution completed",
                project_id=project_id,
                final_status=project.status,
                completed_steps=len([s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED]),
                total_steps=len(project.workflow_steps),
                correlation_id=correlation_id
            )
            
            return project
            
        except Exception as e:
            logger.error(
                "Project workflow execution failed",
                project_id=project_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Update project status
            if project_id in self.projects:
                self.projects[project_id].status = ProjectStatus.FAILED
            
            raise ProjectServiceException(
                f"Failed to execute project workflow for {project_id}",
                "WORKFLOW_EXECUTION_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    def _are_dependencies_completed(
        self,
        step: ProjectStep,
        all_steps: List[ProjectStep]
    ) -> bool:
        """Check if all step dependencies are completed"""
        
        if not step.dependencies:
            return True
        
        # Create lookup of completed step types
        completed_step_types = set()
        for completed_step in all_steps:
            if completed_step.status == ProjectStepStatus.COMPLETED:
                completed_step_types.add(completed_step.step_type)
        
        # Check if all dependencies are satisfied
        for dependency in step.dependencies:
            # Convert dependency string to step type
            dependency_type = None
            for step_type in WorkflowStepType:
                if dependency.replace('_', '') in step_type.value.replace('_', ''):
                    dependency_type = step_type
                    break
            
            if dependency_type and dependency_type not in completed_step_types:
                return False
        
        return True
    
    async def get_project_status(
        self,
        project_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Get current project status and progress"""
        
        try:
            project = self.projects.get(project_id)
            if not project:
                raise ProjectServiceException(f"Project {project_id} not found")
            
            # Calculate progress metrics
            completed_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED]
            in_progress_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.IN_PROGRESS]
            failed_steps = [s for s in project.workflow_steps if s.status == ProjectStepStatus.FAILED]
            
            progress_percentage = (len(completed_steps) / len(project.workflow_steps)) * 100 if project.workflow_steps else 0
            
            # Calculate time metrics
            actual_duration = 0
            if project.started_at:
                end_time = project.completed_at or datetime.utcnow()
                actual_duration = int((end_time - project.started_at).total_seconds() / 60)
            
            return {
                "project_id": project_id,
                "status": project.status,
                "progress_percentage": round(progress_percentage, 1),
                "total_steps": len(project.workflow_steps),
                "completed_steps": len(completed_steps),
                "in_progress_steps": len(in_progress_steps),
                "failed_steps": len(failed_steps),
                "estimated_duration_minutes": project.estimated_duration_minutes,
                "actual_duration_minutes": actual_duration,
                "created_at": project.created_at.isoformat(),
                "started_at": project.started_at.isoformat() if project.started_at else None,
                "completed_at": project.completed_at.isoformat() if project.completed_at else None,
                "current_step": in_progress_steps[0].name if in_progress_steps else None,
                "next_step": self._get_next_pending_step(project.workflow_steps)
            }
            
        except Exception as e:
            logger.error(
                "Failed to get project status",
                project_id=project_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    def _get_next_pending_step(self, workflow_steps: List[ProjectStep]) -> Optional[str]:
        """Get the next pending step name"""
        
        for step in workflow_steps:
            if step.status == ProjectStepStatus.PENDING:
                return step.name
        
        return None
    
    async def get_project_metrics(
        self,
        project_id: str,
        correlation_id: str
    ) -> ProjectMetrics:
        """Get detailed project metrics and analytics"""
        
        try:
            project = self.projects.get(project_id)
            if not project:
                raise ProjectServiceException(f"Project {project_id} not found")
            
            # Calculate step metrics
            step_statuses = {}
            step_durations = {}
            
            for step in project.workflow_steps:
                step_statuses[step.step_type] = step.status
                if step.actual_duration_minutes:
                    step_durations[step.step_type] = step.actual_duration_minutes
            
            # Calculate efficiency metrics
            total_estimated = sum(step.estimated_duration_minutes for step in project.workflow_steps)
            total_actual = sum(step.actual_duration_minutes or 0 for step in project.workflow_steps)
            
            efficiency_ratio = (total_estimated / total_actual) if total_actual > 0 else 1.0
            
            # Calculate quality metrics
            quality_score = self.workflow_orchestrator._calculate_project_quality_score(project)
            
            return ProjectMetrics(
                project_id=project_id,
                total_steps=len(project.workflow_steps),
                completed_steps=len([s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED]),
                failed_steps=len([s for s in project.workflow_steps if s.status == ProjectStepStatus.FAILED]),
                estimated_duration_minutes=total_estimated,
                actual_duration_minutes=total_actual,
                efficiency_ratio=round(efficiency_ratio, 2),
                quality_score=quality_score,
                step_statuses=step_statuses,
                step_durations=step_durations,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(
                "Failed to get project metrics",
                project_id=project_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def retry_failed_step(
        self,
        project_id: str,
        step_id: str,
        correlation_id: str
    ) -> bool:
        """Retry a failed workflow step"""
        
        logger.info(
            "Retrying failed step",
            project_id=project_id,
            step_id=step_id,
            correlation_id=correlation_id
        )
        
        try:
            project = self.projects.get(project_id)
            if not project:
                raise ProjectServiceException(f"Project {project_id} not found")
            
            # Find the failed step
            target_step = None
            for step in project.workflow_steps:
                if step.step_id == step_id:
                    target_step = step
                    break
            
            if not target_step:
                raise ProjectServiceException(f"Step {step_id} not found")
            
            if target_step.status != ProjectStepStatus.FAILED:
                raise ProjectServiceException(f"Step {step_id} is not in failed state")
            
            # Reset step status
            target_step.status = ProjectStepStatus.PENDING
            target_step.error_message = None
            target_step.started_at = None
            target_step.completed_at = None
            target_step.actual_duration_minutes = None
            target_step.output_data = None
            
            # Execute the step
            success, result = await self.workflow_orchestrator.execute_workflow_step(
                project, target_step, correlation_id
            )
            
            logger.info(
                "Step retry completed",
                project_id=project_id,
                step_id=step_id,
                success=success,
                correlation_id=correlation_id
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Step retry failed",
                project_id=project_id,
                step_id=step_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def list_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[ProjectStatus] = None,
        correlation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List projects with optional filtering"""
        
        try:
            projects = list(self.projects.values())
            
            # Apply status filter
            if status_filter:
                projects = [p for p in projects if p.status == status_filter]
            
            # Sort by creation date (newest first)
            projects.sort(key=lambda p: p.created_at, reverse=True)
            
            # Apply pagination
            paginated_projects = projects[offset:offset + limit]
            
            # Convert to summary format
            project_summaries = []
            for project in paginated_projects:
                summary = {
                    "project_id": project.project_id,
                    "name": project.name,
                    "project_type": project.project_type,
                    "building_type": project.building_type,
                    "status": project.status,
                    "progress_percentage": self._calculate_progress_percentage(project),
                    "created_at": project.created_at.isoformat(),
                    "estimated_duration_minutes": project.estimated_duration_minutes,
                    "total_steps": len(project.workflow_steps)
                }
                project_summaries.append(summary)
            
            return project_summaries
            
        except Exception as e:
            logger.error(
                "Failed to list projects",
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    def _calculate_progress_percentage(self, project: Project) -> float:
        """Calculate progress percentage for a project"""
        
        if not project.workflow_steps:
            return 0.0
        
        completed_count = len([s for s in project.workflow_steps if s.status == ProjectStepStatus.COMPLETED])
        total_count = len(project.workflow_steps)
        
        return round((completed_count / total_count) * 100, 1)
    
    async def delete_project(
        self,
        project_id: str,
        correlation_id: str
    ) -> bool:
        """Delete a project and its associated data"""
        
        logger.info(
            "Deleting project",
            project_id=project_id,
            correlation_id=correlation_id
        )
        
        try:
            if project_id not in self.projects:
                raise ProjectServiceException(f"Project {project_id} not found")
            
            project = self.projects[project_id]
            
            # Clean up associated documents from RAG index
            if project.uploaded_documents:
                for doc_id in project.uploaded_documents:
                    try:
                        await self.rag_service.remove_document(doc_id, correlation_id)
                    except Exception as e:
                        logger.warning(
                            "Failed to remove document from RAG index",
                            project_id=project_id,
                            document_id=doc_id,
                            error=str(e)
                        )
            
            # Remove from project storage
            del self.projects[project_id]
            
            logger.info(
                "Project deleted successfully",
                project_id=project_id,
                correlation_id=correlation_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Project deletion failed",
                project_id=project_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def health_check(self, correlation_id: str) -> Dict[str, Any]:
        """Perform health check on project service"""
        
        try:
            return {
                "status": "healthy",
                "total_projects": len(self.projects),
                "active_projects": len([p for p in self.projects.values() if p.status == ProjectStatus.IN_PROGRESS]),
                "service_uptime": "available",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(
                "Project service health check failed",
                error=str(e),
                correlation_id=correlation_id
            )
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


# Global project service instance
project_service = None


def get_project_service(
    ai_service: AIService,
    document_service: DocumentService,
    rag_service: RAGService
) -> ProjectService:
    """Get or create global project service instance"""
    
    global project_service
    
    if project_service is None:
        project_service = ProjectService(
            ai_service=ai_service,
            document_service=document_service,
            rag_service=rag_service
        )
    
    return project_service