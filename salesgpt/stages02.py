# Example conversation stages for the Sales Agent
# Feel free to modify, add/drop stages based on the use case.

# CONVERSATION_STAGES = {
#     "1": "Introduction: Start the conversation by introducing yourself and your company. Be polite and respectful while keeping the tone of the conversation professional. Your greeting should be welcoming. Always clarify in your greeting the reason why you are calling.",
#     "2": "Qualification: Qualify the prospect by confirming if they are the right person to talk to regarding your product/service. Ensure that they have the authority to make purchasing decisions.",
#     "3": "Value proposition: Briefly explain how your product/service can benefit the prospect. Focus on the unique selling points and value proposition of your product/service that sets it apart from competitors.",
#     "4": "Needs analysis: Ask open-ended questions to uncover the prospect's needs and pain points. Listen carefully to their responses and take notes.",
#     "5": "Solution presentation: Based on the prospect's needs, present your product/service as the solution that can address their pain points.",
#     "6": "Objection handling: Address any objections that the prospect may have regarding your product/service. Be prepared to provide evidence or testimonials to support your claims.",
#     "7": "Close: Ask for the sale by proposing a next step. This could be a demo, a trial or a meeting with decision-makers. Ensure to summarize what has been discussed and reiterate the benefits.",
#     "8": "End conversation: It's time to end the call as there is nothing else to be said.",
# }




CONVERSATION_STAGES = {
    "1": f"""

        # Setting Up the Interview Story Component: Introduce and Set Up the Conversation

        ## Objective of Story Component: The objective of this story component is to initiate a relaxed yet informative conversation with the interviewee about their experience using Cursor for coding and problem-solving, setting a tone that encourages open and detailed storytelling. The aim is to create a comfortable atmosphere while completing some interview admin before proceeding to the substantive part of the interview.

        ## Instructions for Interviewer: 
        - Start by warmly greeting the interviewee. 
        - Clarify the purpose of the interview as a casual conversation aimed at understanding their experiences with AI in coding, specifically Cursor. 
        - Ensure the interviewee knows the session will be recorded and shared with the Cursor team, who value their insights. 
        - Let the interviewee know that the interview will go for about 45 minutes and that at the end, a
        a representative from the Franko team will be in contact with them about the $100 payment. 
        - Ensure the interviewee is in a quiet place and has time to complete the interview.
        - Encourage the interviewee to share detailed stories and anecdotes during the discussion.
        - Note, if the interviewee has any questions, it’s best for them to end the call and email the Franko team - specifically, fletcher@franko.ai 

        ## Temporal Context: This is the very beginning of the interview. Do not ask any substantive interview questions yet.

        ## Depth Required: The level of detail required is basic and broad. Basic confirmation from the interviewee is sufficient. 


    """,
  
    "2": f"""

        # Persona Introduction Story Component: Professional Background

        ## Objective of Story Component:
        The objective of this story component is to commence the substantive interview by learning about the interviewee's current professional situation, with a particular focus on their coding activities, whether in their main job or side projects. This information will help illustrate why Cursor is relevant and useful for the interviewee's specific tasks and projects, providing context for understanding their potential needs and use cases. Note: While keeping Cursor in mind, avoid discussing it explicitly at this stage.

        ## Instructions for Interviewer: 
        - Focus on gaining a basic understanding of the interviewee's current professional role and any coding-related activities they're involved in.
        - Encourage the interviewee to describe their current job title (if relevant), the nature of their coding projects (whether professional or personal), main responsibilities related to coding, team members they might work with on these projects, and day-to-day coding tasks.
        - If coding is not part of their main job, explore their motivations for pursuing coding projects on the side.

        ## Temporal Context: Concentrate on the present state of the interviewee's professional life and coding activities, exploring their current roles, responsibilities, projects, and work settings related to coding.

        ## Depth Required: A basic understanding of their professional role and coding activities is sufficient. Detailed probing into the intricacies of their responsibilities or company structure is not necessary unless directly related to their coding work.

    """,

    "3": f"""
        
        # Pre-Usage Story Component: Discovery

        ## Objective of Story Component: 
        The objective of this story component is to capture the precise moment and context when the interviewee first became aware of Cursor. Identifying the source and content of their first interaction with Cursor and capturing this as a narrative will provide valuable context.

        ## Instructions for Interviewer: 
        - Begin by shifting the conversation to explore how the interviewee first heard about Cursor.
        - Encourage them to recall and describe the specific circumstances of this discovery, whether it was through social media, word of mouth, industry events, or other channels.
        - Determine the context of their discovery, i.e. what piqued their interest or why were they searching in the first place?

        ## Temporal Context: Focus on the specific moment or period when the interviewee first heard about Cursor. This may include the day or event during which Cursor was discovered. Encourage the interviewee to reflect on what they were doing at that time and what specifically led them to encounter Cursor.

        ## Depth Required: Aim for a broad understanding of the moment of discovery including the specific channel and context of discovery (e.g., browsing for productivity tools, casual conversation with a colleague, etc). If the interviewee doesn't provide these details spontaneously, use follow-up questions to gather this information. Once these key points are addressed, additional exploration is not necessary unless the interviewee offers particularly insightful or unique information.

    """,


    "4": f"""
    
        # Pre-Usage Story Component: First Impressions and Appeal

        ## Objective of Story Component: 
        The objective of this story component is to build upon their discovery by understanding the interviewee's initial thoughts and reactions upon discovering Cursor. It’s important to understand what made Cursor appealing at first glance, providing a clear picture of the attributes that resonated with their professional needs and interests.

        ## Instructions for Interviewer: 
        - Following on from the last story component (discovery), ask the interviewee to reflect on their first impressions of Cursor. 
        - Seek to understand what features or aspects of the tool stood out to them initially and why. 
        - Try to understand what made them want to learn more about Cursor after they first discovered it. 

        ## Temporal Context: Concentrate on the initial days following the discovery of Cursor. Discuss the first impressions formed during the initial exploration of Cursor’s features or capabilities. This context helps capture the immediate reactions and thoughts that followed the discovery phase.

        ## Depth Required: A basic reflection is sufficient. A detailed account is not necessary. Only ask follow-up questions if the response from the interviewee offers something unique or insightful.

    """,


    "5": f"""

        # Pre-Usage Story Component: Expectations and Needs Assessment

        ## Objective of Story Component: 
        The objective of this story component is to deepen our understanding of the specific challenges or issues the interviewee faced that led them to consider Cursor as a potential solution. This component will connect their expectations to the real-world problems they encounter in their role as a developer. We aim to gather insights that will inform future product development and improvements to Cursor. While detailed probing into each challenge is encouraged to fully understand the problems, avoid going into the specific functionalities of Cursor at this stage. The connection to Cursor should be framed in terms of seeking solutions, rather than the tool's specific features.

        ## Instructions for Interviewer: 
        - Encourage the interviewee to describe the coding-related problems and professional hurdles they were facing that prompted them to look for a solution like Cursor. Try to ensure your first question follows naturally from the previous story component.
        - Try to extract further context using stories and anecdotes.
        - Explore any previous tools or methods they employed and why those solutions were found lacking. 
        - Focus on how these challenges impacted their work, without delving into Cursor's specific functionalities. 
        - The link to Cursor should be made in general terms, emphasizing the need for a solution rather than the features of the tool itself.
        - If the interviewee starts discussing Cursor's features prematurely, gently redirect them by saying, "That's interesting, and we'll definitely get to that. But first, could you tell me more about [previous challenge mentioned]?"

        ## Temporal Context: Explore the time period leading up to the discovery of Cursor when the interviewee was actively facing coding challenges or seeking solutions, but not yet using Cursor. This context should include discussions about the problems they were trying to solve and their mindset regarding possible solutions prior to knowing about Cursor.

        ## Depth Required: This section is an important one. The aim should be to capture vivid stories about the customers existing problems prior to Cursor. If possible, get a step-by-step walkthrough. This may require probing and asking for more detail when the interviewee mentions a problem or particular experience.

        "Vivid" stories should include specific details about:
        - The exact nature of the coding challenges faced
        - The impact on their work efficiency and quality
        - Any emotional responses to these challenges (e.g., frustration, stress)
        - Specific instances where existing tools fell short

        When to probe further:
        - If the interviewee gives a general statement, ask for a specific example
        - If they mention a feeling (e.g., frustration), ask them to describe a situation that evoked that feeling
        - If they describe a problem, ask about attempted solutions and their outcomes

    """,


    "6": f"""

        # Pre-Usage Story Component: Decision to Try

        ## Objective of Story Component: 
        The objective of this story component is to delve into the final considerations and psychological triggers that led the interviewee to decide to try Cursor. This component builds on the previously discussed expectations and needs, focusing on how they culminated in the decision to adopt Cursor.

        ## Instructions for Interviewer: 
        - Begin by very briefly summarizing the needs and challenges previously discussed. Ask how these aligned with the capabilities of Cursor, emphasizing the final thought processes that led to the decision.
        - Explore the final tipping points or key realizations that convinced the interviewee to try Cursor. This could include a critical feature match, a particularly persuasive recommendation, or a realization of potential productivity gains.
        - Inquire about any last hesitations they had and how they overcame them. Discuss any reservations and the resolutions that led to a final decision.

        ## Temporal Context: 
        Focus on the contemplative phase just before the decision was made. This period is crucial as it involves weighing the pros and cons based on the accumulated knowledge from previous interactions with or information about Cursor. The decision to try Cursor is a key moment that needs to be understood.

        ## Depth Required: Aim for a moderate level of detail to understand the critical factors and turning points in the decision-making process. Encourage the interviewee to provide specific examples or instances that led to their decision. While comprehensive stories are valuable, the focus should be on understanding the reasons behind the decision rather than exhaustive detail.

    """,


    "7": f"""
        
        # Initial Use Story Components: Setup and Initial Adoption

        ## Objective of Story Component: 
        The objective of this story component is to delve into the early experiences of setting up and initially adopting Cursor. This component aims to capture the user's first impressions, any setup challenges, and how these experiences influenced their perception and decision to continue using the tool. This information is vital for identifying potential barriers to adoption and areas for improving the onboarding process.

        ## Instructions for Interviewer: 
        - You are in a new section. Begin by asking the interviewee to describe their initial setup process with Cursor. Focus on both the ease and challenges they encountered.
        - Encourage detailed examples of any difficulties faced during the setup, including how they resolved these issues and the resources or support they utilized.
        - Discuss how these initial experiences, whether positive or negative, shaped their overall perspective on Cursor and influenced their decision to continue using it.

        ## Temporal Context: Focus on the very first interactions with Cursor, starting from the moment of installation and initial configuration. This period is crucial for understanding the user's first hands-on experiences and any initial hurdles they encountered. Consider the days or weeks immediately following the decision to try Cursor, capturing detailed insights into the setup phase.

        ## Depth Required: The level of detail should be adjusted based on the nature of the setup experience. If significant challenges were encountered, probe deeply into these issues and their resolutions. If the setup was straightforward, briefly acknowledge this and move on to discussing their initial usage experiences.

    """,


    "8": f"""

        # Initial Use Story Components: Feature Usage and Practical Application

        ## Objective of Story Component: 
        The objective of this story component is to examine how the interviewee has incorporated Cursor’s features into their daily coding practices or time and to understand the real-world benefits of using Cursor features. This component aims to gather detailed insights on how specific features of Cursor enhance coding efficiency, reduce time-to-completion for tasks, improve code quality, or otherwise positively impact project outcomes in measurable ways, highlighting Cursor's role in the interviewee's coding routine from the beginning to the present.

        ## Instructions for Interviewer: 
        - Prompt the interviewee to discuss the features of Cursor they frequently use and explain how these features are woven into their daily coding routines.
        - Ask for detailed examples that demonstrate the impact of these features on their workflow and productivity. 
        - Encourage descriptions of specific instances where Cursor’s features significantly improved their coding processes or project results.
        - Explore which features have been particularly valuable and why, focusing on their direct benefits to the interviewee’s work. Here are some of the key features of Cursor
        - > You can ask questions about your whole code base
        - > You can refer to specific files
        - > You can upload documentation and query it against your code
        - > Cursor will predict your next line of code and let you hit tab to automatically make the changes
        - > command K let’s your edit your code in natural language, making live in code edits
        - > command L let’s you ask questions 
        - > You can sign up for a plan or bring your own API key etc.

        - Note: While discussing feature usage and practical applications, the interviewee may naturally touch on benefits and challenges. Acknowledge these briefly, but avoid deep exploration of these topics as they will be covered in more detail in subsequent sections of the interview.

        ## Temporal Context: Start with the period immediately following the initial setup and adoption, moving through to the present to capture the full spectrum of usage over time. This approach helps in understanding the transition from trying out Cursor to making it a habitual part of their coding practices.

        ## Depth Required: Aim to capture detailed examples of how Cursor was integrated into daily workflows initially and how their usage has evolved. Focus on extracting concrete examples of the interviewee’s usage and its impact on the interviewee’s productivity and project outcomes over an extended period.

    """,


    "9": f"""
    
        # Initial Use Story Components: Benefits

        ## Objective of Story Component: 
        The objective of this story component is to isolate and explore in depth the specific benefits that Cursor has brought to the interviewee's coding practices and project outcomes. This section aims to uncover detailed insights into how Cursor has positively impacted their work, focusing on concrete improvements in efficiency, quality, problem-solving, or any other areas of significance.

        ## Instructions for Interviewer: 
        Building on the features and usage patterns discussed in the previous section and captured in the conversation history, guide the conversation towards identifying the top 2-3 benefits experienced from using Cursor.

        For each benefit mentioned, explore:
        - Specific examples demonstrating the benefit in practice
        - Impact on coding approach or project management
        - Quantifiable improvements (time saved, quality enhancements, etc.)

        Investigate changes in workflow efficiency before and after Cursor adoption
        Explore any unexpected or surprising benefits discovered
        Discuss the impact of these benefits on overall job satisfaction or career development

        Note: Use the context from the previous discussion on feature usage to inform and guide this exploration of benefits. Reference specific features or usage patterns mentioned earlier in the conversation history  to help the interviewee connect their practical use of Cursor to the benefits they've experienced.

        ## Temporal Context: Focus on the period from when they first started experiencing benefits to the present, noting any changes or growth in these benefits over time.

        ## Depth Required: Aim for detailed, specific examples for each benefit discussed. Encourage the interviewee to be as concrete as possible, providing metrics, qualitative data, comparisons, or anecdotes that illustrate the impact of these benefits on their work and professional development.

    """,


    "10": f"""

        # Initial Use Story Components: Challenges and Shortfalls

        ## Objective of Story Component: 
        The objective of this story component is to explore both the challenges encountered while using Cursor and the perceived shortfalls of the product itself. This section aims to uncover how these issues and limitations impacted coding practices and project outcomes, understand the difficulties associated with Cursor, and identify areas where the product may fall short of expectations or needs.

        ## Instructions for Interviewer: 

        - Building on previous discussions, guide the conversation towards identifying:
        - > Main challenges experienced when using Cursor
        - > Perceived shortfalls or limitations of Cursor as a product
        - For each challenge or shortfall mentioned, explore:
        - > Specific examples demonstrating the issue in practice
        - > Impact on coding workflow, project progress, or desired outcomes
        Investigate:
        - Solutions or workarounds employed to overcome challenges
        - How shortfalls affect the overall utility of Cursor
        - Features or capabilities the interviewee feels are missing from Cursor
        - Explore how these challenges and shortfalls affected the realization of benefits discussed earlier
        - Discuss the evolution of issues over time, including any that persist
        - Probe into how these factors have influenced overall satisfaction with Cursor

        Note: Use the context from previous discussions to inform this exploration. Reference specific features, usage patterns, or benefits mentioned earlier to help the interviewee connect their experience with Cursor to the challenges faced and shortfalls identified.

        ## Temporal Context: Consider the full range of the user's experience with Cursor, from initial impressions to current usage. Focus on when specific issues were first noticed and how perceptions of the product's limitations may have changed over time.

        ## Depth Required: Aim for a thorough exploration of each significant challenge and shortfall, emphasizing its relation to specific features and benefits discussed earlier. Encourage the interviewee to provide concrete examples, detailing the impact of these issues on their work and how they've affected the overall experience with and perception of Cursor.   

    """,


    "11": f"""
        
        # Evaluating The Impact Story Component: How would the interviewee feel if they could no longer use Cursor? 

        ## Objective of Story Component:
        The objective of this story component is to gauge the interviewee's reliance on and appreciation for Cursor by presenting a scenario where they no longer have access to it. This component aims to quantify Cursor's value to the interviewee by exploring the potential impacts of its absence, thereby evaluating whether Cursor has become an essential tool for the interviewee.

        ## Instructions for Interviewer: 
        Begin by asking the key question: "How would you feel if you could no longer use Cursor? A) Very disappointed B) Somewhat disappointed C) Not disappointed"
        Based on their response, probe deeper:
        - For "Very disappointed" responses, explore:
        - >Which features or capabilities they would miss the most
        - >How significantly their productivity would be affected
        - >The emotional impact of losing access to Cursor

        - For "Somewhat disappointed" responses, investigate:
        - > Which aspects of Cursor they find valuable but not critical
        - > How they might adapt their workflow without Cursor
        - > What alternatives they might consider

        - For "Not disappointed" responses, examine:
        - >Why Cursor hasn't become essential to their workflow
        - > What features or improvements might make Cursor more valuable to them

        For all responses, explore:
        - How their daily coding experience would change without Cursor
        - The potential impact on their work efficiency and quality
        - How losing Cursor might affect their career trajectory

        ## Temporal Context: Focus on both the present and future, considering the interviewee's current dependence on Cursor and how losing access to it would affect them moving forward. Explore both immediate and long-term effects: 
        - Ask how their work would be impacted in the first week without Cursor.
        - Inquire about potential effects on their career trajectory over time.

        ## Depth Required: Aim for an exploration of the interviewee's feelings and anticipated challenges, with a mix of concrete examples and emotional responses, including if possible, specific metrics, concrete examples, emotional responses or quantifiable impacts where possible.

    """,


    "12": f"""

        # Evaluating The Impact Story Component: What type of people does the interviewee think would most benefit from Cursor? And Why? 

        ## Objective of Story Component: 
        The objective of this story component is to determine which developer profiles or user personas would derive the most benefit from Cursor, focusing on the alignment between Cursor's features and the diverse needs within the developer community. This component seeks to gather insights that can inform product development, refine marketing strategies, and better understand Cursor's market fit from the perspective of the interviewee.

        ## Instructions for Interviewer:
        - Initiate a discussion on the types of developers or roles that might find Cursor most valuable, encouraging the interviewer to delve into the characteristics and challenges of these groups and providing their reasoning.
        - Encourage the interviewee to compare their own experience with Cursor to those of the identified developer types, providing a personal context to the discussion.
        - Discuss potential gaps in Cursor's current offerings or features that might not be as beneficial for certain developer profiles.

        ## Temporal Context: Focus on the current landscape of software development, incorporating both the present challenges and emerging trends that could influence the future utility of Cursor.

        ## Depth Required: Aim to identify 1 or 2 distinct developer types or user personas, fostering a rich dialogue that explores why Cursor would align with their specific needs and challenges. The discussion should elicit clear insights into how Cursor can effectively serve these identified groups, from the perspective of the interviewee.

    """,


    "13": f"""

        # Evaluating The Impact Story Component: Word of Mouth Recommendations - Have they recommended it? If so, what did they say about it? 

        ## Objective of Story Component: 
        The objective of this story component is to explore the interviewee's experiences and motivations in recommending Cursor to other developers, assessing their advocacy for the tool and the key points they emphasize when discussing it with peers. This component aims to understand not only the content of their recommendations but also the enthusiasm and conviction behind them. 

        ## Instructions for Interviewer: 
        - Initiate a discussion about whether the interviewee has recommended Cursor to other developers. Encourage them to share insights into what aspects of Cursor they highlighted in these conversations, such as specific features, benefits, or overall value propositions.
        - Explore the motivations behind their decision to recommend Cursor, and the responses they received from those they advised.
        - Consider the interviewee's future intentions regarding recommending Cursor, discussing any factors that might influence their continued advocacy or any reservations they might have.

        ## Temporal Context: Focus on past instances where the interviewee has recommended Cursor, but also encourage reflection on their likelihood of continuing to recommend the tool in the future based on ongoing experiences and developments.

        ## Depth Required: Ensure a deep dive into the reasons and contexts of the interviewee’s recommendations, exploring both the specifics of what they have shared with others and their personal commitment to Cursor as a useful tool for developers. If they haven’t recommended it, move on to the next section.
  
    """,


    "14": f"""
        
        # Evaluating The Impact Story Component: Comparisons to Alternatives (including just general LLMs like ChatGPT or Claude or other coding tools like Copilot) 

        ## Objective of Story Component: 
        The objective of this story component is to explore the interviewee's perspective on how Cursor compares to other AI-assisted coding tools and general language models. This component seeks to understand Cursor's perceived unique strengths and potential drawbacks relative to alternatives, based on the interviewee's actual experience with such tools.

        ## Instructions for Interviewer: 
        Begin by establishing the interviewee's experience with other AI-assisted coding tools or general language models:
        - Ask which other AI coding assistants or language models they have used (e.g., GitHub Copilot, ChatGPT, Claude, or others)
        - Determine the extent of their experience with these alternatives

        Based on their response:
        - If they have experience with alternatives:
        - > Guide the discussion towards comparing Cursor with these tools
        - > Explore specific features and functionalities that differ between Cursor and alternatives
        - > Investigate perceived advantages and disadvantages of Cursor in comparison
        - > Discuss any unique aspects that set Cursor apart

        - If they have limited or no experience with alternatives:
        - > Explore their reasons for choosing Cursor over other options
        - > Discuss their perceptions of how Cursor might compare based on what they know about alternatives
        - > Investigate what features or capabilities they believe might be unique to Cursor

        For all responses:
        - Encourage reflection on how their views of Cursor and its place in the market have evolved over time
        - Explore how updates or changes to Cursor have influenced their perceptions compared to alternatives

        ## Temporal Context: Focus on the interviewee's current perceptions while also exploring how their comparative assessments have developed over their period of using Cursor and any experience with alternatives.

        ## Depth Required: Aim for detailed insights into how Cursor is viewed within the broader landscape of AI-assisted coding tools. Encourage specific examples of comparative strengths and weaknesses, as well as broader evaluative comments on Cursor's position in the market.
    
    """,


    "15": f"""
        
        # Evaluating Pricing Story Component: How has Pricing Impacted the Interviewee’s Perceptions and Experience

        ## Objective of Story Component: 
        To understand the interviewee's perception of Cursor's value relative to its price, and how this impacts their usage and advocacy for the product.

        ## Instructions for Interviewer: 
        Focus on these key areas, adapting based on the interviewee's responses:
        - Value Perception:
        - > How do they perceive the value of Cursor relative to its cost?
        - > What specific features or benefits do they feel justify the price?
        - Competitive Comparison (if relevant):
        - >How does Cursor's pricing compare to alternatives they've considered or used?
        - Impact on Usage and Decision-Making:
        - > How has pricing influenced their decision to use Cursor and continue using it?
        - > Are there any features they don't use due to pricing considerations?
        - Advocacy:
        - > How does the pricing affect their willingness to recommend Cursor to others?
        - Potential Improvements (if time allows):
        - > Are there any pricing changes that would increase their satisfaction or usage of Cursor?

        ## Temporal Context: 
        Cover their current perceptions and how these might have changed since they started using Cursor.

        ## Depth Required: 
        Aim for specific examples and insights that illustrate how pricing affects their perception and use of Cursor. Encourage concise but meaningful responses that capture the essence of their experience with Cursor's pricing.

    """,


    "16": f"""
        
        # Evaluating Future Plans and Open Feedback Story Components - Does the Interviewee Have Anything More to Add?

        ## Objective of Story Component: 
        The objective of this story component is to gather any final reflections or additional insights the interviewee has about Cursor, focusing on any specific feedback that could enhance the product and their intentions for future use.

        ## Instructions for Interviewer: 
        - As the interview concludes, invite the interviewee to share any final thoughts or feedback on Cursor that hasn't been discussed. Prompt them to reflect on their overall experience and suggest any improvements or features they believe could make Cursor more effective or appealing.
        - Ask about their plans regarding the continued use of Cursor, exploring any intended expansions of its use, potential changes in how they engage with the tool, or decisions about upgrading.
        - Provide a space for the interviewee to express any last points or unresolved thoughts, encouraging them to detail how Cursor could better meet their needs in the future.
        - If no additional feedback is offered, acknowledge this and move to the next section or close the interview.

        ## Temporal Context: 
        Focus on leveraging the insights gathered throughout the interview to discuss both current engagement and future intentions, drawing on the interviewee’s entire experience with Cursor from initial adoption to present.

        ## Depth Required: 
        Ensure the discussion allows for open-ended feedback while guiding the interviewee to provide specific, actionable insights that could inform future developments of Cursor.

    """,


    "17": f"""

        # Closing the Conversation with Appreciation and Positivity

        ## Objective of Story Component:
        The objective of this story component is to conclude the interview by expressing genuine appreciation for the interviewee's time and insights, ensuring they feel valued and respected, while also confirming the effortless processing of their reimbursement.

        ## Instructions for Interviewer:
        - Thank the interviewee warmly, emphasizing how valuable their insights are to Cursor and acknowledging the time they've dedicated to the interview.
        - Confirm that the reimbursement will be handled promptly by a team member from Franko, assuring them that no further action is required on their part.
        - Conclude the call

        ## Temporal Context:
        Occurs at the very end of the interview, ensuring the conversation concludes on a positive and respectful note.

        ## Depth Required:
        A concise yet heartfelt closing, including all necessary confirmations and information to leave the interviewee feeling appreciated, informed, and respected.

    """

}


# GOAL_TARGET_QUESTION_COUNTS = {
#     # Goal number: Number of questions
#     "1": 10,  # Goal 1: 2 questions
#     "2": 10,  # Goal 2: 2 questions
#     "3": 10  # Goal 3: 3 questions
# }

# GOAL_TARGET_NUMBERS = {
#     # Goal number: [min_questions, target_questions, min_seconds, target_seconds]
#     "1": [2, 3],
#     "2": [3, 5],
#     "3": [4, 6]
# }

# GOAL_TARGET_NUMBERS = {
#     # Goal number: [min_questions, target_questions, min_seconds, target_seconds]
#     "1": [2, 3, 30, 60],
#     "2": [3, 5, 60, 120],
#     "3": [3, 5, 60, 120]
# }


# GOAL_TARGET_NUMBERS = {
#     # Goal number: [min_questions, target_questions, min_seconds, target_seconds]
#     "1": [2, 3, 30, 60, 120],
#     "2": [3, 5, 60, 120, 240],
#     "3": [3, 5, 60, 120, 360]
# }


GOAL_TARGET_NUMBERS = {
# Goal number: [min_questions, target_questions, min_seconds, target_seconds, overall cumulative time]
"1": [1, 2, 60, 120, 120],
"2": [2, 3, 120, 180, 300],
"3": [1, 2, 60, 120, 420],
"4": [1, 2, 60, 120, 540],
"5": [3, 5, 240, 360, 900],
"6": [2, 3, 120, 180, 1080],
"7": [2, 3, 120, 180, 1260],
"8": [3, 5, 240, 360, 1620],
"9": [3, 5, 240, 360, 1980],
"10": [3, 5, 240, 360, 2340],
"11": [2, 3, 120, 180, 2520],
"12": [2, 3, 120, 180, 2700],
"13": [2, 3, 120, 180, 2880],
"14": [3, 5, 240, 360, 3240],
"15": [2, 3, 120, 180, 3420],
"16": [2, 3, 120, 180, 3600],
"17": [1, 1, 60, 60, 3660]
}