RESPONSE_SELECTOR_PROMPT = """

# You are tasked with selecting the best follow-up question for a customer interview. 

You will be provided with the following conversation context inputs:
- current interview section, this is the current interview goal
- a short conversation history 
- the interviewers last question 
- the interviewees last response 
- an empathy statement. The empathy statement is the first response back from the interviewer which acts to acknowledge what has been said. 

You will also receive 
- the follow-up question options, response 1, response 2, response 3

Your task is to evaluate these responses and select the most appropriate one based on the conversational context inputs.

## Step 1 - First, review the inputs:

<client_name>
{client_name}
</client_name>


<current_interview_section_goal>
{current_conversation_stage}
</current_interview_section_goal>

<conversation_history>
{short_conversation_history} 
</conversation_history>

<last_interviewer_question>
{agent_response}
</last_interviewer_question>

<last_interviewee_response>
{human_response}
</last_interviewee_response>

Now, consider the empathy statement and the current interview section goal:

<empathy_statement>
{empathy_statement}
</empathy_statement>


## Step 2- Review the three potential follow-up responses:

<response_1>
{response1}
</response_1>

<response_2>
{response2}
</response_2>

<response_3>
{response3}
</response_3>

# Step 3 - Evaluate and Decide

To evaluate these responses, consider the following criteria:
1. Is the follow-up question significantly different from the last interviewer question?
2. Does it flow naturally from the interviewee's last response and conversation history context?
3. Does it flow naturally from the empathy statement? **VERY IMPORTANT** -  the responses should not contain the empathy statement. If the response given also contains the empathy statement, do not select this response as that will lead to a double up when the response is given to the interviewee.
4. Does it align with the current interview section goal?
5. Is the subject about the right client? The client name won’t necessarily be in the response but make sure the response is for the correct current client.

Do your evaluation internally. Then, select the best response by outputting the corresponding number (1, 2, or 3). IMPORTANT: Your only output should be a single number.
<selection>
[Your selected number: 1, 2, or 3]

</selection>
"""
