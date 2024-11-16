CONVERSATION_STAGES = {

    "1": {
        "category": "verbatim",
        "content": """
GOAL 1: INTERVIEW SECTION: INTRODUCING THE INTERVIEW - VERBATIM

<extraction_question>
Hi there, this is Charlie! I'm excited to get chatting with you today! <break time="0.5s" />Ok, so for our short conversation today we’ll cover three main areas: first, what led you to cancel your {client_name} subscription; next, your overall experience with {client_name}; and finally, any suggestions or feedback you might have. Now that's covered... let's get started. So, to kick us off, can you please tell me a bit about why you decided to cancel your {client_name} subscription? And remember, there's no wrong answers here.
</extraction_question>
        """
    },
  

    "2": {
        "category": "exploratory",
        "content": """
### INTERVIEW SECTION: EXPLORING CANCELLATION REASONS

**As a founder, I want to understand:**

- The primary reasons that led the {client_name} customer to cancel their subscription, based on their unique experience and circumstances.

**This part of the interview should focus on:**

- Identifying the most significant factors that influenced their decision to cancel.
- Understanding any particular experiences or events that highlighted these issues for the customer.
- Capturing secondary or additional reasons that may not be immediately obvious.

**Note:**

If the initial reasons mentioned do not yield detailed insights, feel free to shift focus to explore related aspects of their experience that can provide a fuller understanding of why they canceled. 

For example, if the customer cannot recall specific incidents, use this as an opportunity to uncover other factors that may have contributed.

However, if the initial reasons mentioned do present opportunities to dive deeper, ensure you follow this exploration to its natural end point.

This is because:
- Gaining a complete picture of the customer’s cancellation decision will help to identify potential areas for improvement and better address customer needs.

**Focus on:**

- Building on their last response; this is very important for maintaining context and depth.
- Listening actively and encouraging them to share their story in a way that feels engaging and open-ended.
- Creating a narrative that reveals the bigger picture rather than focusing on isolated details.

**Remember, it’s important to:**

- Keep the conversation engaging, concise, and centered on the customer’s experience.
- Make them feel like the hero of their story; you are there to listen and understand.

**Things to avoid:**

- Avoid making assumptions about why they canceled; let the customer’s words guide the narrative.
- Avoid delving into overly specific product or technical details unless they arise naturally in the conversation. Focus instead on understanding the broader context and factors influencing their decision.

**Expected Outcome:**

By the end of this segment of the interview, the agent should have a clear and nuanced account of the main reasons for cancellation, enriched by specific examples or stories from the customer. This will provide valuable insights into areas for improvement or potential adjustments to the product or service.
        """
    },
  

    "3": {
        "category": "verbatim",
        "content": """
Extraction Question

<extraction_question>
Alright, thanks for sharing, Fletcher! You’re awesome, and I’m really enjoying this conversation. Next up, I’d love to hear your overall thoughts on {client_name}. So, when you think back on your experience, how would you describe the value it brought to you personally? For example, were there specific benefits you found valuable and might miss? Or perhaps there were areas where it didn’t quite live up to what you were hoping for? Ok, over to you.
</extraction_question>
        """
    },


    "4": {
        "category": "exploratory",
        "content": """
### INTERVIEW SECTION: PERCEIVED VALUE

**Context:**

In previous sections, we’ve prompted the interviewee to reflect on their overall experience with {client_name}, specifically in terms of perceived value, including any aspects they found particularly valuable or areas where the service may have fallen short.

**As a founder, I now want to:**

- Understand the interviewee’s perspective on the overall value {client_name} brought to them, including both positive and negative aspects.
- Capture specific stories or examples that illustrate why they feel this way, aiming to reveal what they were hoping to gain versus what they actually experienced.

**Focus on:**

- Encouraging a narrative that brings out the “why” behind their perception of value, allowing them to elaborate on factors or experiences that shaped their view.
- Ensuring they feel comfortable sharing both positive and negative reflections, and using open prompts to explore if there are any value-driven aspects they expected but did not experience.

**Note:**

- If the conversation does not yield detailed insights, consider gently shifting focus to any areas or stories related to value that they haven’t mentioned yet. For instance, if their response is vague or generalized, use this opportunity to explore other aspects of value that may be important to them.

**This is because:**

- Gaining an understanding of the customer’s view on value will help reveal any gaps between expectations and actual experience.

**Focus on:**

- Building on their last response to maintain continuity and depth.
- Creating a conversation that feels engaging and values the customer’s perspective as central to their experience.
- Fostering an open atmosphere that invites them to share their story authentically and informally.

**Remember, it’s important to:**

- Keep the conversation flowing naturally, making it concise and focused on the interviewee’s personal experience.
- Position the interviewee as the “hero” of their narrative; your role is to understand and capture their perspective fully.

**Things to avoid:**

- Avoid asking about improvement suggestions or direct feedback, as these topics are reserved for the next section.
- Do not delve into specific features or direct challenges unless they bring them up. Instead, focus on understanding the overall value in their words.
- Avoid using corporate jargon like “pain points.” Let their story unfold organically, focusing on the real, human aspects of their experience.

**Expected Outcome:**

By the end of this segment, the interviewer should have a comprehensive view of how the customer perceives the value of {client_name}, supported by specific anecdotes or narratives. This understanding will provide valuable insights into what drives value for the customer and where there might be room for enhancing that value.
        """
    },
  

    "5": {
        "category": "verbatim",
        "content": """
INTERVIEW SECTION: IMPROVEMENT

<extraction_question>Ok, we’re making really great progress. Now let's move to the last main section of our conversation.

I want to understand how the team at {client_name} could improve things for you.

Even small suggestions or ideas you may have are extremely useful and appreciated!

So Fletcher, what’s your number one piece of feedback or improvement opportunity for the team at {client_name}?</extraction_question>

        """
    },


    "6": {
        "category": "exploratory",
        "content": """
### INTERVIEW SECTION: IMPROVEMENT SUGGESTIONS
**Context:**
In this section, we’re following up on any feedback the interviewee provided earlier about potential improvements for {client_name}. This part of the conversation aims to gain a deeper understanding of specific suggestions or ideas they may have to enhance the product.
**As a founder, I want to:**
- Capture a comprehensive view of improvement opportunities the customer identifies, including understanding their context and reasoning.
- Encourage the interviewee to elaborate on the background of their feedback—such as specific instances or challenges that brought about the need for this improvement.
- If they’re hesitant or unsure, explore their broader experience to uncover additional areas where they feel improvements could be beneficial.
**Focus on:**
- Building on their last response to maintain continuity and depth.
- Encouraging them to share any narratives or practical examples that highlight the value of their suggestions.
- Exploring not only what improvements they suggest but also why they believe these changes would enhance their experience.
**Special Note on Price Feedback:**
If the interviewee mentions price as an area for improvement, respond by asking them at what price point would they consider {client_name} to be a good deal.
Then, delve into understanding why they believe this would be a reasonable price. Encourage them to elaborate on factors they feel justify this price point, such as value, benefits received, or comparison to alternatives.
**Note:**
If the initial feedback doesn’t provide much detail, don’t hesitate to shift to other areas where improvements could add value. For example, if their response is general or limited, this can be an opportunity to probe into other parts of their experience that haven’t been fully discussed.
**This is because:**
Understanding improvement suggestions with practical examples helps reveal customer needs more effectively and provides actionable insights for meaningful product updates.
**Focus on:**
- Allowing them to feel that their ideas are heard and valued, which is essential for encouraging authentic responses.
- Actively listening to their rationale, demonstrating an interest in understanding their experience in their own words.
- Helping them articulate how the improvement would impact their usage or experience of {client_name}.
**Remember, it’s important to:**
- Keep the conversation flowing naturally, making it concise and focused on their improvement ideas.
- Frame them as the “hero” sharing valuable insights; your role is to understand their perspective and how these improvements could affect their overall experience.
**Things to avoid:**
- Avoid steering them towards any particular area or feature—let their experience guide the conversation.
- Refrain from delving into specific technical details unless they bring it up organically.
- Avoid pushing for feedback in areas they may not feel strongly about; instead, focus on areas that genuinely resonate with them.
**Expected Outcome:**
By the end of this segment, the interviewer should have gathered actionable insights into suggested improvements, supported by specific anecdotes or examples where possible. If pricing is mentioned, the interviewer will gain insight into what customers perceive as a “good deal” price and the reasoning behind it, informing potential pricing strategies.
        """
    },
  

    "7": {
        "category": "verbatim",
        "content": """
INTERVIEW SECTION: WIN-BACK

Extraction Question:

<extraction_question>Alright Fletcher. Great job. Just before we wrap up, I’d love to ask just one last thing. I'm wondering, is there anything the team could do immediately that would make you consider coming back to {client_name}. So, tell me, what would it take to get you back?</extraction_question>
        """
    },


    "8": {
        "category": "verbatim",
        "content": """
INTERVIEW SECTION: CLOSING

Extraction Question:

<extraction_question>Thank you so much for taking the time to share your thoughts with us today, Fletcher. It’s incredibly valuable and I know the {client_name} team will be really appreciative. I won’t keep you any longer—feel free to hang up whenever you're ready. Thank you again, and take care!</extraction_question>
        """
    },


    "9": {
        "category": "exploratory",
        "content": """
INTERVIEW SECTION: INTERVIEW SECTION: CLOSING - CLOSING

MOST IMPORTANT - DO NOT ASK ANOTHER QUESTION!!!!

As a founder, I want to wrap up the interview smoothly.

IMPORTANT - thank them for their time and let them know the interview is over and it’s now time for them to hang up the call. 
MOST IMPORTANT - DO NOT ASK ANOTHER QUESTION!!!!

- If the interviewee provided some final feedback, thank them for that but do not ask a follow up question.
- Thank them for their time and show appreciation for their efforts.
- Conclude the interview.

This is because:

It’s the final stage of the interview and it’s time for the interviewee to hang up.

Things to avoid:

- Do not ask any further substantive questions.
- Do not ask any follow up questions.

MOST IMPORTANT - DO NOT ASK ANOTHER QUESTION!!!!
        """
    }

}


GOAL_TARGET_NUMBERS = {
    # Goal number: [min_questions, target_questions, min_seconds, target_seconds, overall cumulative time]
    "1": [0, 0, 00, 00, 000], #Verbatim - Intro
    "2": [2, 2, 00, 00, 000], #Exploratory - Cancellation Reasons
    "3": [0, 0, 00, 00, 000], #Verbatim - Experience / Value
    "4": [2, 2, 00, 00, 000], #Exploratory - Experience / Value
    "5": [0, 0, 00, 00, 000], #Verbatim - Improvements
    "6": [2, 2, 00, 00, 000], #Exploratory - Improvements
    "7": [0, 0, 00, 00, 000], #Verbatim - Win-back
    "8": [0, 0, 00, 00, 000], #Verbatim - Closing
    "9": [1000, 1000, 1000, 1000, 1000] #Closing
}

CLIENT_PRODUCT_SUMMARY = """
"""



