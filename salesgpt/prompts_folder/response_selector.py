RESPONSE_SELECTOR_PROMPT = """

# You are tasked with selecting the best follow-up question for a customer interview.
You will be provided with the following conversation context inputs:
- **Current Interview Section**: The objective of the current interview section.
- **Short Conversation History**: A brief overview of the recent exchanges between the interviewer and the interviewee.
- **Interviewer's Last Question**: The last question asked by the interviewer.
- **Interviewee's Last Response**: The last response given by the interviewee.
- **Empathy Statement**: A statement that is the first dialogue from the interviewer to acknowledge what the interviewee has said. It is separate from the response being picked here and should not be included.
You will also receive:
- **Three Follow-Up Question Options**: Response 1, Response 2, Response 3.
Your task is to evaluate these responses based on the conversational context and select the most appropriate one.
## Step 1 - First, review the inputs:
<Client Name>
{client_name}
</Client Name>
<Current Interview Section Goal>
{current_conversation_stage}
</Current Interview Section Goal>
<Conversation History>
{short_conversation_history}
</Conversation History>
<Last Interviewer Question>
{agent_response}
</Last Interviewer Question>
<Last Interviewee Response>
{human_response}
</Last Interviewee Response>
Now, consider the empathy statement and the current interview section goal:
<Empathy Statement>
{empathy_statement}
</Empathy Statement>
## Reminder:
Remember, the follow-up question you choose should **not** include or duplicate the above empathy statement.
## Step 2 - Review the three potential follow-up responses:
<Response 1>
{response1}
</Response 1>
<Response 2>
{response2}
</Response 2>
<Response 3>
{response3}
</Response 3>
# Step 3 - Evaluate and Decide
Before making your selection, use this checklist to ensure the follow-up question meets the necessary criteria:
- [ ] Does not contain the empathy statement to avoid redundancy.
- [ ] Is significantly different from the last interviewer question.
- [ ] Flows naturally from the interviewee's last response.
- [ ] Aligns with the objectives of the current interview section.
- [ ] Is relevant to the client discussed.
- [ ] Double check because very important - the response does not contain the empathy statement to avoid redundancy.
To ensure the selection of the most appropriate follow-up question, consider the guidelines and checklist above, and carry out your evaluation internally.
Then, select the best response by noting the corresponding number (1, 2, or 3). **IMPORTANT**: Your output should only be the selected number.
<Selection>
[Your Selected Number: 1, 2, or 3]
</Selection>
"""