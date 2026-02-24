# Workshop Lab Restructuring Requirements Summary

## Introduction

This document outlines the requirements for restructuring the translation agent workshop from its current 4-lab format into a new 6-lab structure organized across two distinct categories: Fundamentals and Advanced. The restructuring aims to provide participants with a clearer learning progression by establishing a strict separation between basic prompting techniques and agentic patterns. This approach ensures that learners build a solid foundation in core concepts before advancing to more complex autonomous system patterns.

## Glossary

The workshop represents the complete set of educational materials teaching translation agent patterns. Each lab is a single Jupyter notebook containing exercises and learning objectives. The Fundamentals category encompasses labs 1-3, which cover basic prompting without introducing agentic concepts. The Advanced category includes labs 4-6, which focus on agentic patterns using the Strands framework. Content migration refers to the process of moving code and explanations between labs during restructuring. A Strands Agent is the agentic framework that uses the @tool decorator and Agent class. Learning objectives are specific skills or concepts students should master in each lab, while prerequisites represent the knowledge or skills required before starting a particular lab.

## Fundamentals Category Overview

The workshop will contain exactly three labs in the Fundamentals category. When a participant completes this category, they will not have been introduced to any Strands Agent concepts. These labs will use only basic Bedrock API calls or simple prompting patterns, deliberately avoiding the @tool decorator or Agent class with tools. The Fundamentals category will cover prompting basics, style and tone customization, and evaluation fundamentals in a logical sequence that builds upon each previous lab.

## Lab 1: Basic Prompting Techniques

The first lab introduces participants to core prompting patterns with Bedrock, helping them understand how to create effective prompts for translation tasks. This lab will retain the Bedrock setup and basic Agent creation from the current first lab, along with one-shot translation examples and prompt engineering techniques. It will also preserve the quality issue identification content while adding new material on core prompting patterns, system prompt structure, and temperature and parameter tuning. Importantly, this lab will not use any tools or agentic patterns. When Lab 1 creates an Agent, it will do so without any tools parameter. The lab is designed to be completed in approximately 15-20 minutes.

## Lab 2: Style, Tone & Terminology

The second lab teaches participants how to customize translation style and handle domain-specific terminology so they can produce translations matching specific requirements. This lab will retain technical terminology handling, AWS service name preservation patterns, and formal tone guidance from the current labs. It will add new content on customizing translation style, handling domain-specific terminology, and maintaining tone consistency. The lab will demonstrate style variations through prompt engineering only, without using tools or agentic self-evaluation. All customization will be achieved through system prompt modifications and parameter tuning. Like Lab 1, this lab is designed to be completed in approximately 15-20 minutes.

## Lab 3: Evaluation Basics

The third lab focuses on teaching participants how to evaluate translation quality manually, ensuring they understand quality criteria before learning automated evaluation techniques. This lab will retain manual quality assessment techniques and translation issue identification from the current first lab. It will add new content on evaluation criteria including accuracy, fluency, terminology, and tone, as well as quality metrics and scoring. The lab will cover human evaluation best practices and demonstrate manual comparison of translation outputs. Critically, this lab will not use automated evaluation tools or self-evaluation patterns, instead preparing participants for the automated evaluation concepts they will encounter in Lab 5. This lab is designed to be completed in approximately 15-20 minutes.

## Advanced Category Overview

The workshop will contain exactly three labs in the Advanced category. This category represents the first place where Strands Agent concepts appear in the workshop. When a participant starts Lab 4, they will be introduced to the @tool decorator and the Agent class with tools for the first time. The Advanced category will cover agentic translation, self-evaluation, and deployment in a sequence that builds upon the foundational knowledge established in the Fundamentals category.

## Lab 4: Agentic Translation

The fourth lab marks a significant transition as it is the first lab introducing Strands Agent patterns. This lab will retain Strands Agent creation patterns, tool creation with the @tool decorator, and agent workflow patterns from the current third lab. It will add new content on multi-step agentic workflows, tool-based translation approaches, and autonomous decision-making patterns. The lab will explicitly state that this is the first introduction to agentic concepts and will provide clear contrast with the non-agentic approaches used in Labs 1-3. This lab is designed to be completed in approximately 20-25 minutes.

## Lab 5: Self-Evaluation

The fifth lab teaches participants how agents can evaluate and improve their own work, enabling them to build self-correcting systems. This lab will retain the evaluate_translation_quality tool, refine_translation_section tool, and iterative refinement loop patterns from the current fourth lab. It will add new content on agent self-assessment techniques, quality-driven iteration strategies, and reflect-refine patterns. The lab will demonstrate how agents autonomously improve output and show quality score progression across iterations. Lab 4 is a required prerequisite for this lab, which is designed to be completed in approximately 20-25 minutes.

## Lab 6: Agent Deployment

The sixth and final lab teaches participants how to deploy agents to production, enabling them to operationalize their translation systems. This lab will retain Knowledge Base integration and CloudFormation deployment from the current second lab, along with production patterns from the current fifth lab. It will add new content on Bedrock AgentCore deployment, production readiness considerations, and monitoring and observability. The lab will demonstrate a complete deployment workflow and show how to test production endpoints. Both Labs 4 and 5 are required prerequisites for this lab, which is designed to be completed in approximately 25-30 minutes.

## Content Migration Requirements

All existing content must be properly migrated to the new lab structure to ensure no educational value is lost during restructuring. When content is migrated from old labs, all code examples, explanatory text, and learning objectives must be preserved. Content should not be duplicated across multiple labs, and nothing should be lost during migration. Strands Agent content must be placed only in the Advanced category, while basic prompting content must be placed only in the Fundamentals category. All cross-references between labs must be updated after migration to reflect the new structure.

## Learning Progression and Prerequisites

Each lab has clearly defined prerequisites that establish the required knowledge before starting. Lab 1 has no prerequisites as it is the entry point. Lab 2 requires Lab 1 completion. Lab 3 requires completion of both Labs 1 and 2. Lab 4 requires completion of Labs 1, 2, and 3. Lab 5 requires Lab 4 completion. Lab 6 requires completion of both Labs 4 and 5. When a lab lists prerequisites, it must explicitly state them in the introduction. When a lab uses concepts from prerequisite labs, it must reference the source lab to help participants connect the concepts.

## Strands Concept Isolation

The workshop maintains strict separation between basic and agentic concepts to ensure participants don't encounter advanced patterns prematurely. The workshop will not use Strands Agent, the @tool decorator, or the Agent class with tools parameter in Labs 1, 2, or 3. When Lab 4 introduces Strands Agent, it must explain why this approach differs from previous labs and provide clear examples of the @tool decorator. The Fundamentals category will use only BedrockModel and basic Agent instantiation with model and system_prompt parameters. If a Fundamentals lab needs to demonstrate evaluation, it must use manual comparison only.

## File Naming and Organization

The workshop follows consistent file naming conventions to make the lab sequence clear and maintainable. Lab 1 is named "lab1-fundamentals-basic-prompting.ipynb", Lab 2 is "lab2-fundamentals-style-tone-terminology.ipynb", and Lab 3 is "lab3-fundamentals-evaluation-basics.ipynb". Lab 4 is named "lab4-advanced-agentic-translation.ipynb", Lab 5 is "lab5-advanced-self-evaluation.ipynb", and Lab 6 is "lab6-advanced-deployment.ipynb". The workshop maintains the lab_helpers directory with shared utilities, the sample_data directory with test documents, and the infrastructure directory with CloudFormation templates.

## Learning Objective Clarity

Each lab provides clear learning objectives so participants know what skills they will gain. When a lab begins, it lists 3-5 specific learning objectives. When a lab ends, it summarizes what was learned using checkmarks to indicate completed objectives and previews the next lab's focus area. When a lab introduces new concepts, it explains why they matter and connects learning objectives to real-world applications, helping participants understand the practical value of what they're learning.

## Code Example Consistency

The workshop uses consistent code patterns across all labs so participants can focus on new concepts rather than syntax changes. Import statements, model configuration, and helper function calls remain consistent across all labs. When a lab introduces new code patterns, it highlights the differences to draw attention to what has changed. The same BedrockModel configuration and variable naming conventions are used throughout all labs, creating a cohesive learning experience.

## Backward Compatibility

The workshop preserves all helper functions and utilities to ensure existing infrastructure continues to work. All functions in lab_helpers/utils.py and lab_helpers/translation_tools.py are retained. All CloudFormation templates in the infrastructure directory and sample data files in sample_data remain unchanged. Helper functions are imported consistently across labs, and no existing infrastructure code is broken during the restructuring process.

## Evaluation Continuity Across Labs

The workshop ensures that evaluation techniques taught in Lab 3 are consistently applied throughout subsequent labs, allowing participants to track translation quality improvements as they learn advanced techniques. Lab 3 establishes baseline evaluation criteria covering accuracy, fluency, terminology, and tone. Lab 4 references these Lab 3 evaluation criteria when introducing agentic translation. Lab 5 uses the Lab 3 evaluation criteria in automated self-evaluation tools. Lab 6 demonstrates quality assessment using Lab 3 criteria in production deployment. When Labs 4-6 evaluate translations, they explicitly compare results against the Lab 3 baseline, showing progressive quality improvement from Lab 3's manual evaluation through Lab 6's production deployment. When a lab introduces new evaluation approaches, it maps them to Lab 3 criteria. The workshop maintains consistent quality scoring on a 0-100 scale across all labs, enabling participants to see measurable improvements in translation quality as they progress through increasingly sophisticated techniques.

## Helper Function Documentation and Mapping

The workshop provides comprehensive documentation of all helper functions and their usage across labs. The requirements document includes a complete inventory of helper functions from utils.py (infrastructure and AWS utilities), translation_tools.py (translation agent tools), translation_agent.py (OpsBuddy agent), and production_agent.py (AgentCore production agent). Each function is mapped to the specific labs that use it, making dependencies clear for workshop maintainers.

Several helper functions have been identified as incomplete and flagged for review. In translation_tools.py, the evaluate_translation_quality, query_terminology_kb, translate_text, and refine_translation_section tools currently return prompt templates or instruction strings instead of executing actual logic. In production_agent.py, the evaluate_translation_quality tool returns a placeholder dictionary, and refine_translation_section returns an instruction string rather than performing refinement. The translation_agent.py file contains an OpsBuddy agent designed for operations monitoring rather than translation, which needs to be reviewed and potentially adapted for translation use cases or replaced with a translation-specific agent class.

The requirements specify which labs use each helper function. For example, utils.py functions like print_section_header, print_success, print_error, and print_info are used across all labs for formatting and feedback. The check_bedrock_model_access function is used in Lab 1 for setup validation. Knowledge Base-related functions like create_s3_bucket_for_kb, upload_terminology_to_s3, wait_for_kb_ingestion, and query_knowledge_base are used in Lab 6 for deployment. Translation tools like evaluate_translation_quality and refine_translation_section are used in Labs 5 and 6, while extract_technical_terms is used in Labs 2 and 4.

## Helper Function Implementation Completion

The workshop requires that all incomplete helper functions be identified and completed before lab deployment. All @tool functions in translation_tools.py and production_agent.py must be fully implemented. The translation_agent.py file must be reviewed and adapted for translation use cases. The workshop must document whether tools should return prompts or execute logic as part of their design pattern. When a tool returns a prompt, this must be clearly documented as the intended pattern. When a tool should execute logic, the execution logic must be implemented. All tools used in labs must be fully functional before lab deployment to ensure participants have a smooth learning experience without encountering incomplete or placeholder implementations.
