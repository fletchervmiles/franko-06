CONVERSATION_STAGES = {

    "1": {
        "category": "verbatim",
        "content": """
GOAL 1: INTERVIEW SECTION: INTRODUCING THE INTERVIEW - VERBATIM

Extraction Question:
<extraction_question>Hi there, this is Charlie!</extraction_question>
        """
    },
  

    "2": {
        "category": "verbatim",
        "content": """
GOAL 2: INTERVIEW SECTION: INTERVIEW SECTION: DISCOVERY - VERBATIM

Extraction Question

<extraction_question>To kick off the first part of our conversation, <break time="0.3s" /> I'd love to hear how you first discovered AgeMate. <break time="0.5s" />So,<break time="0.4s" /> can you remember when you first came across it <break time="0.3s" />and perhaps<break time="0.3s" /> any first impressions of AgeMate you may have had at the time?</extraction_question>
        """
    },

    "3": {
        "category": "exploratory",
        "content": """
GOAL 3: INTERVIEW SECTION: INTERVIEW SECTION: DISCOVERY - EXPLORATORY

As a founder, I want to understand:

The complete story of how the interviewee first discovered AgeMate, focusing on:
- The conditions and context when they encountered AgeMate.
- Whether they were actively seeking a solution, and what motivated that search.
  - Were they addressing a specific problem?
  - Was the discovery facilitated by recommendations or influential sources?
  - Any other compelling reasons or accidental findings?

Note: If the initial focus does not yield detailed insights, don’t be afraid to shift to related aspects of the discovery narrative. For example, if the interviewee cannot recall specifics, use this as an opportunity to probe other factors or circumstances that might have led them to discover and adopt the tool.

This is because:

These insights provide valuable data on customer acquisition pathways and refine product positioning strategies.

Focus on:

- Building on previous responses, drawing out deeper insights into their discovery narrative.
- If specifics are unclear or the response is vague, shift the focus to explore broader search behaviors or motivations. 
- Cultivating a narrative that conveys the larger context rather than isolated details.

Remember, it’s important to:

- Keep the conversation engaging, streamlined, and centered on the interviewee.
- Elevate them as the center of their story, listening to comprehend and depict their journey comprehensively.
- Use any gaps or uncertainties in their responses to investigate further aspects of their discovery narrative, such as motivations or unforeseen needs that led to using AgeMate.

Things to avoid:

- Avoid asking about AgeMate features or benefits. This is because this topic will have a specific section later in the interview. For now, it’s about understanding the interviewee and their experiences and preferences.
- Avoid asking for specifics or challenges. Focus on learning more, asking questions that allow the interviewee to give you a story in their own words. You’re there to listen and let their story unfold, not ask them corporate jargon like “what are your pain points?” AVOID THIS.
        """
    },
  

    "4": {
        "category": "verbatim",
        "content": """
Extraction Question

<extraction_question>Ok, thanks for sharing how you discovered AgeMate. <break time="0.75s" />Now, I'd love for you to think back to the point when you actually made the purchase. <break time="0.75s" />Do you remember if there was anything that made you hesitate or have second thoughts before clicking the buy button? <break time="0.5s" /> And I guess if so, what ultimately convinced you to go ahead with your purchase anyway?</extraction_question>
        """
    },


    "5": {
        "category": "verbatim",
        "content": """
GOAL 5: INTERVIEW SECTION: INTERVIEW SECTION: MAIN BENEFITS - VERBATIM

Extraction Question:

<extraction_question>Alright, thanks for completing the first part of the interview. <break time="0.75s" /> By the way, you’re awesome {interviewee_name}, I’m really enjoying our conversation.<break time="0.75s" />. So, next up, I'd love to hear about the most significant benefit you received from using AgeMate. <break time="0.75s" />Can you please describe this benefit to me using your own words?</extraction_question>
        """
    },
  

    "6": {
        "category": "exploratory",
        "content": """

GOAL 6: INTERVIEW SECTION: INTERVIEW SECTION: MAIN BENEFITS - EXPLORATORY

Context:

In the recent conversation history, we have asked the interviewee about the main benefit they receive from AgeMate.

That was followed up by a request to give a concrete example of the benefit in their day to day work life. 

As a founder, I now want to:

- help the interviewee give a full end-to-end narrative driven example of what they perceive as the main benefit - so if they haven’t quite done that yet, help them by asking a contextually relevant follow-up question.

- If the example is sufficiently comprehensive, let’s ask the interviewee to share the practical implications that result from the benefit they’ve discussed. Maybe it’s with their time, on their project, on their collaboration, etc. Whatever it is, it should be in their words with anecdotal evidence, if possible.

Here’s example language (include something similar to this in analysis 5):

“You mentioned [state tangible example/s of benefit from their narrative]. I’d love it if you could share with me what you see as the practical implications of this? Like, what does this actually mean for your day to day?”

Ultimately, the objective is to comprehend their given example to its fullest, thereby appreciating the benefit in its true manifestation. If possible, understanding the practical implications will be very valuable.

Note: If the current conversation does not yield detailed insights, don’t be afraid to shift to asking about different benefits. For example, if the interviewee cannot recall specifics or gives a vague response, use this as an opportunity to probe other factors or circumstances listed in the interview section that might have not been discussed yet.

This is because:

We want to facilitate and help the interviewee share the full narrative of their story.

Focus on:

- Building on their last response, this is very important.
- Learning more about them, your attitude should be “wow, so interesting, I’d love to learn more”.
- Stimulating a narrative that paints the bigger picture rather than delving into minor details.

Remember, it’s important to:

- Keep the conversation engaging, brief, and focused on the interviewee. 
- Making them the hero of the story, we're here to listen, understand, and paint a picture of who they are.

Things to avoid:

- Do not ask whether they have recommended the product to other - there’s a separate section for this topic
- Do not ask about improvement suggestions - there’s a separate section for this topic
- Do not ask about specific problems or challenges - there’s a separate section for this topic
- Do not ask direct questions or about features - there’s a separate section for this topic
- Avoid asking for specifics or challenges. Focus on learning more, asking questions that allow the interviewee to give you a story in their own words. You’re there to listen and let their story unfold, not ask them corporate jargon like “what are your pain points?” AVOID THIS.
        """
    },


    "7": {
        "category": "verbatim",
        "content": """
GOAL 7: INTERVIEW SECTION: INTERVIEW SECTION: IMPROVEMENT - VERBATIM


Extraction Question:

<extraction_question>Thanks so much for giving your perspective on the main benefit, now let's move to the next part of the interview.<break time="0.75s" />I want to understand how the team at AgeMate could improve the product for you.<break time="0.5s" />Even small things are extremely useful and appreciated!<break time="0.3s" />So {interviewee_name}, can you think of any feedback or improvement opportunities for the team at AgeMate?</extraction_question>
        """
    },


    "8": {
        "category": "exploratory",
        "content": """
GOAL 8: INTERVIEW SECTION: INTERVIEW SECTION: IMPROVEMENT - EXPLORATORY

Context:

In the recent conversation history, we have asked the interviewee any improvements they have in mind for AgeMate.

As a founder, I want to understand improvements suggestions from the interviewee.

- If they have not provided an example of an improvement, gently nudge them again, stressing the importance of their inputs
- if they have a suggestion, seek to understand the context further. We need to understand their reasoning and practical desire for their suggestions. For example, when did the lack of this feature last impact them? What task were they trying to accomplish?
- If they are unsure, shift to broader aspects of their experience to uncover any other areas for improvement.

Note: If the current conversation does not yield detailed insights, don’t be afraid to shift to asking about different improvement opportunities. For example, if the interviewee cannot recall specifics or gives a vague response, use this as an opportunity to probe other factors or circumstances listed in the interview section that might have not been discussed yet.


This is because:

We want to facilitate and help the interviewee expand on their feedback.

Focus on:

- Building on their last response, this is very important.
- Learning more about them, your attitude should be “wow, so interesting, I’d love to learn more”.
- Stimulating a narrative that paints the bigger picture rather than delving into minor details.

Remember, it’s important to:

- Keep the conversation engaging, brief, and focused on the interviewee. 
- Making them the hero of the story, we're here to listen, understand, and paint a picture of who they are.

Things to avoid:

- Do not ask whether they have recommended the product to other - there’s a separate section for this topic
- Do not ask about specific problems or challenges - there’s a separate section for this topic
- Do not ask direct questions or about features - there’s a separate section for this topic
- Avoid asking for specifics or challenges. Focus on learning more, asking questions that allow the interviewee to give you a story in their own words. You’re there to listen and let their story unfold, not ask them corporate jargon like “what are your pain points?” AVOID THIS.
        """
    },
  

    "9": {
        "category": "verbatim",
        "content": """
GOAL 9: INTERVIEW SECTION: INTERVIEW SECTION: OPEN FEEDBACK AND CLOSING - VERBATIM

Extraction Question:

<extraction_question>Alright, you’ve almost done it, {interviewee_name}! Just one more question.<break time="0.5s" />So, before we wrap up, I’d love to know if there’s anything specific the team at AgeMate could do to win you back as a customer. <break time="0.5s" />For example, would enhancements in ingredients, pricing changes or anything else that comes to mind,<break time="0.5s" /> make a difference in your decision to cancel your plan?</extraction_question>
        """
    },

    "10": {
        "category": "exploratory",
        "content": """
GOAL 30: INTERVIEW SECTION: INTERVIEW SECTION: CLOSING - CLOSING

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
    "2": [0, 0, 00, 00, 000], #Verbatim - Discovery
    "3": [0, 0, 00, 00, 000], #Exploratory - Discovery
    "4": [0, 0, 00, 00, 000], #Verbatim - Conversion
    "5": [0, 0, 00, 00, 000], #Verbatim - Main Benefit
    "6": [0, 0, 00, 00, 000], #Exploratory - Main Benefit 
    "7": [0, 0, 00, 00, 000], #Verbatim - Improvements
    "8": [0, 0, 00, 00, 000], #Exploratory - Improvements
    "9": [0, 0, 00, 00, 000], #Verbatim - Win back
    "10": [1000, 1000, 1000, 1000, 1000] #Closing - Closing
}

CLIENT_PRODUCT_SUMMARY = """
AgeMate is an Australian company specializing in dietary supplements aimed at addressing the root causes of aging. Their flagship product, the Daily Longevity Blend, is a ready-to-mix powder that combines 18 research-backed ingredients, including Nicotinamide Mononucleotide (NMN), Pterostilbene, Glycine, Hyaluronic Acid, L-Theanine, Magnesium Malate, MSM, Spermidine, and vitamins C, D3, and K2. This blend is formulated to support energy levels, cognitive clarity, and overall well-being.

Founded in May 2022 and officially launched in November 2022, AgeMate is based in Melbourne, Australia. The company emphasizes transparency and quality, sourcing their products from trusted suppliers and conducting third-party testing to ensure purity and efficacy.

AgeMate's mission is to improve the lives of millions globally by helping prevent age-related illnesses through the latest findings in the field of longevity.
"""



