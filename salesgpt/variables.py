"""

EMPATHY AND CONTEXT CHAIN
- client_name
- conversation_history

KEY POINTS CHAIN
- client_name
- conversation_history

SPECIFIC CONTEXT CHAIN
- client_name
- client_product_summary
- conversation_history

CONVERSATION SUMMARY CHAIN
- client_name
- conversation_history

CURRENT GOAL REVIEW CHAIN
- current_conversation_stage
- conversaton_history
- client_name

GOALS / STAGES (not sure how the variables get to these? Stage Analzyer and current goal review)
- interviewee_name
- conversation_history
- customer_type

QUESTION COUNT
- interviewee_name
- client_name
- lead_interviwer (NEW)
- stage_counts (NEW)
- conversation_stage_id
- goal_target_question_counts (NEW)

GOAL COMPLETION STATUS
- client_name
- current_conversation_stage
- conversation_history

STAGE ANALYZER
- goal_completeness_status (NEW)
- question_count_summary (NEW)
- conversation_stage_id

TRANSITION PROMPT
- interviewer_name
- has_progressed (NEW)
- current_conversation_stage

"""