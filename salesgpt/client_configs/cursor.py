CONVERSATION_STAGES = {
    "1": f"""
**Current Customer Interview Section: Interview Introduction:**

The goal for this opening section is to establish a comfortable atmosphere by setting the stage for a relaxed, engaging interview. We'll handle preliminary logistics, confirm the interview setup, and ensure the interviewee is ready and informed about the interview's structure and duration, without discussing substantive topics yet. 

**Objectives:**

- Objective 1 - A Warm Greeting:
- > Start by warmly greeting the interviewee and clarifying that the purpose of the interview is a casual conversation aimed at understanding their experiences with AI in coding, specifically Cursor. 

- Objective 2 - Mention Recording:
- > Mentioned that the interview will be recorded and shared with the Cursor team, who value their insights (explicit consent not required).

- Objective 3 - Time Confirmation:
- > Let the interviewee know that the interview will go for about 45 minutes - ensure they are in a quiet place and currently have time to complete the interview.

- Objective 4 - Payment Information:
- > Let the interviewee know that following the completion of the interview, a representative from the Franko team will be in touch to process their $100 payment for completing the interview.
    """,
  
    "2": f"""
**Current Interview Section: Persona and Professional Background:**

The goal for this section is to begin the substantive part of the interview by exploring the interviewee's current professional role and coding activities. This discussion will provide context for understanding how Cursor could be relevant and useful in their tasks and projects, focusing on the present state of their career to ensure relevance and timeliness. Note, while keeping Cursor in mind, avoid discussing it explicitly at this stage.

**Objectives:**

- Objective 1 - Professional Role and Coding Interests:
- > The goal for this section is to begin the substantive part of the interview by exploring the interviewee's current professional role and coding activities. This discussion will provide context for understanding how Cursor could be relevant and useful in their tasks and projects, focusing on the present state of their career to ensure relevance and timeliness. Basic level details are sufficient to establish context without delving into deep specifics.

- Objective 2 - Project Details:
- > Encourage the interviewee to describe specific projects they are involved in, focusing on the nature and scope of these projects. This should include details about both professional coding projects and / or personal side projects.

- Objective 3 - Daily Tasks and Collaboration:
- > Investigate the interviewee's day-to-day coding tasks and any collaborative aspects of their projects. This objective aims to uncover how they interact with team members and manage coding tasks on a regular basis, providing insights into their operational environment.
    """,

    "3": f"""
**Current Interview Section: Discovery and Initial Impressions of Cursor:**

The goal for this combined section is to trace the interviewee's journey from the moment they first became aware of Cursor to their initial reactions and the aspects of the tool that captured their interest. This narrative aims to seamlessly link the discovery of Cursor to the perceived benefits or features that made it appealing, focusing on how these elements resonated with their professional needs and existing real-world problems they face as a developer.

**Objectives:**

- Objective 1 - Recall Discovery:
- > Encourage the interviewee to describe the specific circumstances under which they discovered Cursor. For example, the circumstances could be via an ad on social media, or word of mouth during a discussion with a friend, a demo at an industry event, or many other possible situations, etc.

- Objective 2 - Reflect on First Impressions:
- > Prompt the interviewee to reflect on their first impressions of Cursor. Using the context from their discovery, explore what specifically stood out about Cursor during their initial encounter. Explore why these perceived benefits, specific features or overall design of the tool stood out. 

- Objective 3 - Needs Assessment
- > Take a step back in the discussion, and let the interviewee know you’re doing so, and reorient towards understanding what the interviewee perceives as their biggest coding-related problems or challenges. Ideally, but not necessarily, this will be connected to the perceived benefits or features they found appealing in their first impressions.
-> Aim to have the interviewee talk through a concrete example of a time they experienced this problem or challenge. This is prior to using Cursor and Cursor should not be the focus here. 

- Objective 4 - Other Solutions
- > In the context of the information learned from the needs assessment section, explore any other tools or methods the interviewee used to solve these problems.
-> If they had, aim to understand why those tools were inadequate and encourage them to share stories and anecdotes that illustrate what was lacking in the tools they previously employed. 

- Objective 5 - Identify Decision Factors:
- > Try to clarify the key factor that ultimately convinced the interviewee to try Cursor, including the key potential benefit, recommendation, specific feature, etc. 
- > Further, investigate whether there were any last minute hesitations, reservations or concerns that the interviewee had to overcome before ultimately making the decision to try Cursor. This objective seeks to understand both the positive influences and the challenges overcome in their decision-making process, providing a comprehensive view of what led them to adopt Cursor.
    """,


    "4": f"""
**Current Interview Section: Setup, Feature Usages, Benefits and Challenges**

The goal of this section is to explore the interviewee's experience with Cursor from onboarding to regular usage, focusing on its integration into their workflow and impact on coding practices. It aims to uncover Cursor's most valuable features and benefits, supported by concrete examples and quantifiable improvements. The section also seeks to identify challenges and areas for improvement, providing a balanced view of the user's experience.

- Objective 1 - Onboarding Experience Impact:
- > Investigate the interviewee’s onboarding experience with Cursor, from installation to initial use. Your aim is to identify any key positive or negative aspects of this process by learning about the experience of the interviewee. If relevant, i.e. if some negative aspects were undercovered, explore how the interviewee revolved these issues and uncover any suggestions they may have for improving the onboarding process.

- Objective 2: Cursor's Integration, Impact, and Benefits:
- > Investigate how the interviewee has incorporated Cursor's features into their daily coding practices, exploring the evolution of usage from initial adoption to present.
- > Identify the most frequently used features, gathering specific examples that demonstrate their impact on workflow, productivity, and code quality.
- > Explore the top 2-3 benefits experienced from using Cursor, supported by concrete examples and quantifiable improvements (e.g., time saved, efficiency gains, quality enhancements, other anecdotes or surprising benefits). 
- > Discuss how Cursor's features and benefits have influenced overall job satisfaction and contributed to professional growth or career development.

- Objective 3 - Cursor's Challenges, Shortfalls, and User Adaptation:
- > Identify the main challenges experienced when using Cursor and the perceived shortfalls or limitations of the product, gathering specific examples that illustrate how these issues impact coding workflow and project outcomes.
- > Explore solutions or workarounds employed to overcome challenges, and discuss how shortfalls affect the overall utility of Cursor in the interviewee's work.
- > Investigate features or capabilities the interviewee feels are missing from Cursor, and how their absence affects the realization of benefits discussed earlier.

- Objective 4 - Test Relative Preference of Features
- >Using conversation history from objective 2 and objective 3 as context, ask the interviewee to state, as a summary of the previous two objectives, the feature which is most important to them about Cursor and the feature which is least important to them. Note, the most frequently used features may not be the most valuable.
    """,

    "5": f"""
**Current Interview Section: Cursor vs. Competitors: Comparative Analysis**

This section aims to position Cursor within the AI coding tool landscape by comparing it to alternatives. We'll explore Cursor's unique features, strengths, and weaknesses relative to other tools, building on earlier discussions about its capabilities. The goal is to understand Cursor's competitive advantages, areas for improvement, and overall value proposition, including its pricing structure compared to alternatives.

- Objective 1 - Cursor’s Comparative Analysis
- > Explore the interviewee's experience with other AI coding tools and language models.
- > Investigate Cursor's perceived strengths and unique features as well as weaknesses and shortcomings compared to alternatives. As much as possible, tie this back to insights and discussion points about the conversation history about features, benefits and weaknesses.
- >How does Cursor's pricing compare to alternatives they've considered or used?
    """,

    "6": f"""
 **Current Interview Section: How would the interviewee feel if they could no longer use Cursor**

This section aims to gauge the interviewee's reliance on and appreciation for Cursor by presenting a scenario where they no longer have access to it. This component aims to quantify Cursor's value to the interviewee by exploring the potential impacts of its absence, thereby evaluating whether Cursor has become an essential tool for the interviewee.

Objective 1 - Begin by asking the interviewee this key question verbatim: "How would you feel if you could no longer use Cursor? A) Very disappointed B) Somewhat disappointed C) Not disappointed"
- > For any level of disappointment, probe deeply to understand the underlying reasons. For "Very disappointed," explore the most missed features, productivity impacts, and emotional effects of losing Cursor. For "Somewhat disappointed," investigate what's valuable but not critical, potential workflow adaptations, and alternatives. For "Not disappointed," examine why Cursor isn't essential and what could enhance its value. Across all responses, the goal is to uncover the 'why' behind their feelings.   
    """,

    "7": f"""
**Current Interview Section: Perspectives on Cursor's Ideal Users**

This section aims to understand the interviewee's view of Cursor through their experiences recommending it to others and their thoughts on who benefits most from the tool. By exploring these external perspectives, we seek to gain objective insights into Cursor's perceived strengths and target audience.

- Objective 1 - Developer Persona Analysis:
- > Identify 1-2 distinct developer types or user personas that would benefit most from Cursor, according to the interviewee.
- > Explore why Cursor aligns with the specific needs and challenges of these identified groups.

Objective 2 - Cursor Advocacy Exploration:
- > Investigate whether the interviewee has recommended Cursor to other developers, including those identified in objective 1.
- > If yes, try to ascertain the conversation that was had, i.e. what aspects of Cursor were highlighted, what reasoning was given or what context set of the discussion. etc.
    """,

    "8": f"""
GOAL 8

# Evaluating Pricing Story Component: Price Sensitivity

This section aims to understand the interviewee's perception of Cursor's value relative to its price, and how this impacts their usage and advocacy for the product. The focus is on conducting a Van Westendorp Price Sensitivity survey.

- Objective 1 - Too Expensive Question
- > Ask the interviewee the following: “At what price would you consider the product to be so expensive that you would not consider buying it?” 

- Objective 2 - Too Cheap Question
- > Ask the interviewee the following verbatim: “At what price would you consider the product to be priced so low that you would feel the quality couldn’t be very good?”

- Objective 3 - Bargain / Good Value Question
- > Ask the interviewee the following verbatim: “At what price would you consider the product to be a bargain—a great buy for the money?”

- Objective 4 - Expensive / High Side Question
- > Ask the interviewee the following verbatim: “At what price would you consider the product to be starting to get expensive, but you still might consider buying it?”

- Objective 5 - Final Conclusions on Pricing
- > Ascertain whether the interviewee has anything further to add regarding pricing.
    """,

    "9": f"""
**Current Interview Section: Open-Ended Insight Gathering and Closing with Appreciation and Positivity:**

The goal for this section is to conclude the interview on a high note, ensuring that the interviewee feels valued and appreciated for their participation and insights and confirming the processing of their reimbursement.

Objective 1 - Open-Ended Insight Gathering
- > Invite the interviewee to share any additional thoughts, feedback, or insights about Cursor that haven't been discussed, focusing on potential improvements or features that could enhance its effectiveness.

- Objective 2: - Confirm Reimbursement and Conclude the Interview
- > Assure the interviewee that the reimbursement will be handled promptly by a team member from Franko and that no further action is required on their part. 

- Objective 3: - Express Gratitude and Confirm the End of the Interview
- > Warmly thank the interviewee for their participation and insights, emphasizing how valuable their contribution has been to Cursor. This is the conclusion of the interview. It’s time to hang up the call.
    """
}


GOAL_TARGET_NUMBERS = {
    # Goal number: [min_questions, target_questions, min_seconds, target_seconds, overall cumulative time]
    "1": [3, 4, 90, 120, 120],
    "2": [3, 4, 180, 240, 360],
    "3": [5, 6, 300, 360, 720],
    "4": [5, 7, 420, 540, 1260],
    "5": [2, 3, 180, 240, 1500],
    "6": [2, 3, 180, 240, 1740],
    "7": [2, 3, 180, 240, 1980],
    "8": [5, 6, 300, 360, 2340],
    "9": [2, 3, 180, 240, 2580]
}