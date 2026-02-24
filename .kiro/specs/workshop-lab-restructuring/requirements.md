# Requirements Document: Workshop Lab Restructuring

## Introduction

This document specifies the requirements for restructuring the translation agent workshop from 4 labs into 6 labs organized across 2 categories (Fundamentals and Advanced). The restructuring aims to provide a clearer learning progression, with strict separation between basic prompting techniques and agentic patterns.

## Glossary

- **Workshop**: The complete set of educational materials teaching translation agent patterns
- **Lab**: A single Jupyter notebook containing exercises and learning objectives
- **Fundamentals_Category**: Labs 1-3 covering basic prompting without agentic concepts
- **Advanced_Category**: Labs 4-6 covering agentic patterns with Strands framework
- **Content_Migration**: The process of moving code and explanations between labs
- **Strands_Agent**: The agentic framework using @tool decorator and Agent class
- **Learning_Objective**: A specific skill or concept students should master in a lab
- **Prerequisite**: Knowledge or skills required before starting a lab

## Requirements

### Requirement 1: Fundamentals Category Structure

**User Story:** As a workshop participant, I want to learn basic prompting techniques before agentic concepts, so that I build foundational skills progressively.

#### Acceptance Criteria

1. THE Workshop SHALL contain exactly 3 labs in the Fundamentals_Category
2. WHEN a participant completes Fundamentals_Category, THE Workshop SHALL NOT have introduced Strands_Agent concepts
3. THE Fundamentals_Category SHALL use only basic Bedrock API calls or simple prompting patterns
4. THE Fundamentals_Category SHALL NOT use the @tool decorator or Agent class with tools
5. THE Fundamentals_Category SHALL cover prompting, style/tone, and evaluation basics in sequence

### Requirement 2: Lab 1 - Basic Prompting Techniques

**User Story:** As a workshop participant, I want to learn core prompting patterns with Bedrock, so that I understand how to create effective prompts for translation tasks.

#### Acceptance Criteria

1. THE Lab1 SHALL retain Bedrock setup and basic Agent creation from current lab1
2. THE Lab1 SHALL retain one-shot translation examples from current lab1
3. THE Lab1 SHALL retain prompt engineering techniques from current lab1
4. THE Lab1 SHALL retain quality issue identification from current lab1
5. THE Lab1 SHALL add content on core prompting patterns not currently covered
6. THE Lab1 SHALL add content on system prompts and their structure
7. THE Lab1 SHALL add content on temperature and parameter tuning
8. THE Lab1 SHALL NOT use any tools or agentic patterns
9. WHEN Lab1 creates an Agent, THE Agent SHALL have no tools parameter
10. THE Lab1 SHALL complete in approximately 15-20 minutes

### Requirement 3: Lab 2 - Style, Tone & Terminology

**User Story:** As a workshop participant, I want to learn how to customize translation style and handle domain-specific terminology, so that I can produce translations matching specific requirements.

#### Acceptance Criteria

1. THE Lab2 SHALL retain technical terminology handling from current labs
2. THE Lab2 SHALL retain AWS service name preservation patterns from current labs
3. THE Lab2 SHALL retain formal tone guidance from current labs
4. THE Lab2 SHALL add content on customizing translation style
5. THE Lab2 SHALL add content on handling domain-specific terminology
6. THE Lab2 SHALL add content on maintaining tone consistency
7. THE Lab2 SHALL demonstrate style variations through prompt engineering only
8. THE Lab2 SHALL NOT use tools or agentic self-evaluation
9. THE Lab2 SHALL use only system prompt modifications and parameter tuning
10. THE Lab2 SHALL complete in approximately 15-20 minutes

### Requirement 4: Lab 3 - Evaluation Basics

**User Story:** As a workshop participant, I want to learn how to evaluate translation quality manually, so that I understand quality criteria before learning automated evaluation.

#### Acceptance Criteria

1. THE Lab3 SHALL retain manual quality assessment techniques from current lab1
2. THE Lab3 SHALL retain translation issue identification from current lab1
3. THE Lab3 SHALL add content on evaluation criteria (accuracy, fluency, terminology, tone)
4. THE Lab3 SHALL add content on quality metrics and scoring
5. THE Lab3 SHALL add content on human evaluation best practices
6. THE Lab3 SHALL demonstrate manual comparison of translation outputs
7. THE Lab3 SHALL NOT use automated evaluation tools
8. THE Lab3 SHALL NOT use self-evaluation patterns
9. THE Lab3 SHALL prepare participants for automated evaluation in Lab 5
10. THE Lab3 SHALL complete in approximately 15-20 minutes

### Requirement 5: Advanced Category Structure

**User Story:** As a workshop participant, I want to learn agentic patterns after mastering fundamentals, so that I can build autonomous translation systems.

#### Acceptance Criteria

1. THE Workshop SHALL contain exactly 3 labs in the Advanced_Category
2. THE Advanced_Category SHALL be the FIRST place where Strands_Agent concepts appear
3. WHEN a participant starts Lab4, THE Workshop SHALL introduce the @tool decorator
4. WHEN a participant starts Lab4, THE Workshop SHALL introduce Agent class with tools
5. THE Advanced_Category SHALL cover agentic translation, self-evaluation, and deployment in sequence

### Requirement 6: Lab 4 - Agentic Translation

**User Story:** As a workshop participant, I want to learn how to create agents with tools, so that I can build multi-step agentic workflows.

#### Acceptance Criteria

1. THE Lab4 SHALL be the FIRST lab introducing Strands_Agent patterns
2. THE Lab4 SHALL retain Strands Agent creation patterns from current lab3
3. THE Lab4 SHALL retain tool creation with @tool decorator from current lab3
4. THE Lab4 SHALL retain agent workflow patterns from current lab3
5. THE Lab4 SHALL add content on multi-step agentic workflows
6. THE Lab4 SHALL add content on tool-based translation approaches
7. THE Lab4 SHALL add content on autonomous decision-making patterns
8. THE Lab4 SHALL explicitly state this is the first introduction to agentic concepts
9. THE Lab4 SHALL provide clear contrast with Labs 1-3 non-agentic approaches
10. THE Lab4 SHALL complete in approximately 20-25 minutes

### Requirement 7: Lab 5 - Self-Evaluation

**User Story:** As a workshop participant, I want to learn how agents can evaluate and improve their own work, so that I can build self-correcting systems.

#### Acceptance Criteria

1. THE Lab5 SHALL retain evaluate_translation_quality tool from current lab4
2. THE Lab5 SHALL retain refine_translation_section tool from current lab4
3. THE Lab5 SHALL retain iterative refinement loop patterns from current lab4
4. THE Lab5 SHALL add content on agent self-assessment techniques
5. THE Lab5 SHALL add content on quality-driven iteration strategies
6. THE Lab5 SHALL add content on reflect-refine patterns
7. THE Lab5 SHALL demonstrate how agents autonomously improve output
8. THE Lab5 SHALL show quality score progression across iterations
9. THE Lab5 SHALL require Lab4 as a prerequisite
10. THE Lab5 SHALL complete in approximately 20-25 minutes

### Requirement 8: Lab 6 - Agent Deployment

**User Story:** As a workshop participant, I want to learn how to deploy agents to production, so that I can operationalize my translation systems.

#### Acceptance Criteria

1. THE Lab6 SHALL retain Knowledge Base integration from current lab2
2. THE Lab6 SHALL retain CloudFormation deployment from current lab2
3. THE Lab6 SHALL retain production patterns from current lab5
4. THE Lab6 SHALL add content on Bedrock AgentCore deployment
5. THE Lab6 SHALL add content on production readiness considerations
6. THE Lab6 SHALL add content on monitoring and observability
7. THE Lab6 SHALL demonstrate complete deployment workflow
8. THE Lab6 SHALL show how to test production endpoints
9. THE Lab6 SHALL require Labs 4 and 5 as prerequisites
10. THE Lab6 SHALL complete in approximately 25-30 minutes

### Requirement 9: Content Migration Accuracy

**User Story:** As a workshop maintainer, I want all existing content properly migrated to new labs, so that no educational value is lost during restructuring.

#### Acceptance Criteria

1. WHEN content is migrated from old labs, THE System SHALL preserve all code examples
2. WHEN content is migrated from old labs, THE System SHALL preserve all explanatory text
3. WHEN content is migrated from old labs, THE System SHALL preserve all learning objectives
4. THE System SHALL NOT duplicate content across multiple labs
5. THE System SHALL NOT lose any content during migration
6. WHEN Strands_Agent content is migrated, THE System SHALL place it only in Advanced_Category
7. WHEN basic prompting content is migrated, THE System SHALL place it only in Fundamentals_Category
8. THE System SHALL update all cross-references between labs after migration

### Requirement 10: Learning Progression and Prerequisites

**User Story:** As a workshop participant, I want clear prerequisites for each lab, so that I know what knowledge is required before starting.

#### Acceptance Criteria

1. THE Lab1 SHALL have no prerequisites
2. THE Lab2 SHALL require Lab1 completion as prerequisite
3. THE Lab3 SHALL require Labs 1 and 2 completion as prerequisites
4. THE Lab4 SHALL require Labs 1, 2, and 3 completion as prerequisites
5. THE Lab5 SHALL require Lab4 completion as prerequisite
6. THE Lab6 SHALL require Labs 4 and 5 completion as prerequisites
7. WHEN a lab lists prerequisites, THE Lab SHALL explicitly state them in the introduction
8. WHEN a lab uses concepts from prerequisites, THE Lab SHALL reference the source lab

### Requirement 11: Strands Concept Isolation

**User Story:** As a workshop designer, I want strict separation between basic and agentic concepts, so that participants don't encounter advanced patterns prematurely.

#### Acceptance Criteria

1. THE Workshop SHALL NOT use Strands_Agent in Labs 1, 2, or 3
2. THE Workshop SHALL NOT use @tool decorator in Labs 1, 2, or 3
3. THE Workshop SHALL NOT use Agent class with tools parameter in Labs 1, 2, or 3
4. WHEN Lab4 introduces Strands_Agent, THE Lab SHALL explain why it differs from previous labs
5. WHEN Lab4 introduces @tool decorator, THE Lab SHALL provide clear examples
6. THE Workshop SHALL use only BedrockModel and basic Agent(model, system_prompt) in Fundamentals_Category
7. IF a Fundamentals lab needs to demonstrate evaluation, THE Lab SHALL use manual comparison only

### Requirement 12: File Naming and Organization

**User Story:** As a workshop maintainer, I want consistent file naming, so that the lab sequence is clear and maintainable.

#### Acceptance Criteria

1. THE Lab1 SHALL be named "lab1-fundamentals-basic-prompting.ipynb"
2. THE Lab2 SHALL be named "lab2-fundamentals-style-tone-terminology.ipynb"
3. THE Lab3 SHALL be named "lab3-fundamentals-evaluation-basics.ipynb"
4. THE Lab4 SHALL be named "lab4-advanced-agentic-translation.ipynb"
5. THE Lab5 SHALL be named "lab5-advanced-self-evaluation.ipynb"
6. THE Lab6 SHALL be named "lab6-advanced-deployment.ipynb"
7. THE Workshop SHALL maintain lab_helpers directory with shared utilities
8. THE Workshop SHALL maintain sample_data directory with test documents
9. THE Workshop SHALL maintain infrastructure directory with CloudFormation templates

### Requirement 13: Learning Objective Clarity

**User Story:** As a workshop participant, I want clear learning objectives for each lab, so that I know what skills I will gain.

#### Acceptance Criteria

1. WHEN a lab begins, THE Lab SHALL list 3-5 specific learning objectives
2. WHEN a lab ends, THE Lab SHALL summarize what was learned
3. THE Lab SHALL use checkmarks (✅) to indicate completed objectives
4. THE Lab SHALL preview the next lab's focus area
5. WHEN a lab introduces new concepts, THE Lab SHALL explain why they matter
6. THE Lab SHALL connect learning objectives to real-world applications

### Requirement 14: Code Example Consistency

**User Story:** As a workshop participant, I want consistent code patterns across labs, so that I can focus on new concepts rather than syntax changes.

#### Acceptance Criteria

1. THE Workshop SHALL use consistent import statements across all labs
2. THE Workshop SHALL use consistent model configuration across all labs
3. THE Workshop SHALL use consistent helper function calls across all labs
4. WHEN a lab introduces new code patterns, THE Lab SHALL highlight the differences
5. THE Workshop SHALL use the same BedrockModel configuration in all labs
6. THE Workshop SHALL use consistent variable naming conventions across all labs

### Requirement 15: Backward Compatibility

**User Story:** As a workshop maintainer, I want to preserve helper functions and utilities, so that existing infrastructure continues to work.

#### Acceptance Criteria

1. THE Workshop SHALL retain all functions in lab_helpers/utils.py
2. THE Workshop SHALL retain all functions in lab_helpers/translation_tools.py
3. THE Workshop SHALL retain all CloudFormation templates in infrastructure/
4. THE Workshop SHALL retain all sample data files in sample_data/
5. WHEN helper functions are used, THE Labs SHALL import them consistently
6. THE Workshop SHALL NOT break existing infrastructure code

### Requirement 16: Evaluation Continuity Across Labs

**User Story:** As a workshop participant, I want to apply evaluation techniques consistently across labs, so that I can track translation quality improvements as I learn advanced techniques.

#### Acceptance Criteria

1. THE Lab3 SHALL establish baseline evaluation criteria (accuracy, fluency, terminology, tone)
2. THE Lab4 SHALL reference Lab3 evaluation criteria when introducing agentic translation
3. THE Lab5 SHALL use Lab3 evaluation criteria in automated self-evaluation tools
4. THE Lab6 SHALL demonstrate quality assessment using Lab3 criteria in production deployment
5. WHEN Labs 4-6 evaluate translations, THE Labs SHALL explicitly compare results against Lab3 baseline
6. THE Workshop SHALL show progressive quality improvement from Lab3 (manual) through Lab6 (production)
7. WHEN a lab introduces new evaluation approaches, THE Lab SHALL map them to Lab3 criteria
8. THE Workshop SHALL maintain consistent quality scoring (0-100 scale) across all labs

### Requirement 17: Helper Function Documentation and Mapping

**User Story:** As a workshop maintainer, I want clear documentation of helper functions and their usage, so that I understand which labs depend on which utilities.

#### Acceptance Criteria

1. THE Requirements SHALL document all helper functions from lab_helpers/utils.py with lab mappings
2. THE Requirements SHALL document all helper functions from lab_helpers/translation_tools.py with lab mappings
3. THE Requirements SHALL document all helper functions from lab_helpers/translation_agent.py with lab mappings
4. THE Requirements SHALL document all helper functions from lab_helpers/production_agent.py with lab mappings
5. WHEN a helper function is incomplete, THE Requirements SHALL flag it for review
6. THE Requirements SHALL specify which labs use each helper function
7. THE Requirements SHALL identify helper functions that need implementation completion

#### Helper Function Inventory

**utils.py - Infrastructure and AWS Utilities:**
- `get_aws_region()` - Used in: All labs (setup)
- `get_account_id()` - Used in: Lab 6 (deployment)
- `check_bedrock_model_access()` - Used in: Lab 1 (setup validation)
- `create_s3_bucket_for_kb()` - Used in: Lab 6 (Knowledge Base setup)
- `upload_terminology_to_s3()` - Used in: Lab 6 (Knowledge Base data)
- `wait_for_kb_ingestion()` - Used in: Lab 6 (Knowledge Base deployment)
- `query_knowledge_base()` - Used in: Lab 6 (Knowledge Base testing)
- `print_section_header()` - Used in: All labs (formatting)
- `print_success()` - Used in: All labs (feedback)
- `print_error()` - Used in: All labs (error handling)
- `print_info()` - Used in: All labs (information display)

**translation_tools.py - Translation Agent Tools:**
- `@tool evaluate_translation_quality()` - Used in: Lab 5 (self-evaluation), Lab 6 (production)
  - ⚠️ INCOMPLETE: Returns prompt template instead of actual evaluation logic
- `@tool query_terminology_kb()` - Used in: Lab 5, Lab 6 (terminology lookup)
  - ⚠️ INCOMPLETE: Placeholder implementation, needs actual KB query logic
- `@tool translate_text()` - Used in: Lab 4, Lab 5, Lab 6 (agentic translation)
  - ⚠️ INCOMPLETE: Returns instruction string instead of performing translation
- `@tool refine_translation_section()` - Used in: Lab 5 (iterative refinement), Lab 6 (production)
  - ⚠️ INCOMPLETE: Returns guidance prompt instead of actual refinement logic
- `extract_technical_terms()` - Used in: Lab 2 (terminology identification), Lab 4 (agentic workflows)
- `format_translation_result()` - Used in: Lab 4, Lab 5, Lab 6 (result formatting)

**translation_agent.py - OpsBuddy Agent (Strands-based):**
- `OpsBuddyAgent` class - Used in: Lab 6 (production deployment example)
  - ⚠️ REVIEW NEEDED: Designed for operations, not translation - may need adaptation
- `OpsBuddyAgent.invoke()` - Used in: Lab 6 (agent invocation)
- `OpsBuddyAgent.chat()` - Used in: Lab 6 (interactive chat)
- `create_ops_buddy()` - Used in: Lab 6 (agent factory)
- `@tool retrieve_from_knowledge_base()` - Used in: Lab 6 (KB retrieval)
- `@tool get_cloudwatch_alarms()` - Used in: Lab 6 (monitoring example)
  - ⚠️ NOT APPLICABLE: CloudWatch monitoring not relevant to translation workshop
- `@tool query_bedrock_model()` - Used in: Lab 6 (direct model queries)

**production_agent.py - AgentCore Production Agent:**
- `app` (BedrockAgentCoreApp) - Used in: Lab 6 (AgentCore deployment)
- `@tool evaluate_translation_quality()` - Used in: Lab 6 (production evaluation)
  - ⚠️ INCOMPLETE: Returns placeholder dict with evaluation_prompt instead of actual evaluation
- `@tool query_aws_terminology()` - Used in: Lab 6 (production terminology lookup)
  - ⚠️ PARTIALLY COMPLETE: Has KB query logic but needs error handling improvements
- `@tool refine_translation_section()` - Used in: Lab 6 (production refinement)
  - ⚠️ INCOMPLETE: Returns instruction string instead of performing refinement
- `invoke()` entrypoint - Used in: Lab 6 (AgentCore handler)

#### Functions Requiring Implementation Review

1. **translation_tools.py - All @tool functions** - Currently return prompts/instructions instead of executing logic. These need to be implemented as actual tools that perform operations or clearly documented as "prompt-returning tools" if that's the intended design pattern.

2. **translation_agent.py - OpsBuddyAgent** - Designed for operations monitoring, not translation. Should either be:
   - Renamed and adapted for translation workflows
   - Replaced with a translation-specific agent class
   - Documented as an example only (not for actual use)

3. **production_agent.py - evaluate_translation_quality()** - Returns placeholder dict. Needs actual evaluation logic or integration with Bedrock model for assessment.

4. **production_agent.py - refine_translation_section()** - Returns instruction string. Needs actual refinement implementation.

### Requirement 18: Helper Function Implementation Completion

**User Story:** As a workshop developer, I want incomplete helper functions identified and completed, so that labs can use fully functional utilities.

#### Acceptance Criteria

1. THE Workshop SHALL complete implementation of all @tool functions in translation_tools.py
2. THE Workshop SHALL complete implementation of all @tool functions in production_agent.py
3. THE Workshop SHALL review and adapt translation_agent.py for translation use cases
4. THE Workshop SHALL document whether tools should return prompts or execute logic
5. WHEN a tool returns a prompt, THE Workshop SHALL clearly document this as the intended pattern
6. WHEN a tool should execute logic, THE Workshop SHALL implement the execution logic
7. THE Workshop SHALL ensure all tools used in labs are fully functional before lab deployment
