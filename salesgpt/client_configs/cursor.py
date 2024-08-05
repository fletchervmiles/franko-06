


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

- Objective 5 (optional) - Interviewee Query: 
- > If the interviewee has any questions, it’s best for them to end the call and email the Franko team. If the interviewee has no questions, no need to mention this objective. Consider it as complete.
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
**Current Interview Section: Closing with Appreciation and Positivity:**

The goal for this section is to conclude the interview on a high note, ensuring that the interviewee feels valued and appreciated for their participation and insights and confirming the processing of their reimbursement.

**Objectives**

- Objective 1: - Express Gratitude and Confirm the End of the Interview
- > Warmly thank the interviewee for their participation and insights, emphasizing how valuable their contribution has been to Cursor. 

- Objective 2: - Confirm Reimbursement and Conclude the Interview
- > Assure the interviewee that the reimbursement will be handled promptly by a team member from Franko and that no further action is required on their part. This is the conclusion of the interview. It’s time to hang up the call.
    """

}



GOAL_TARGET_NUMBERS = {
# Goal number: [min_questions, target_questions, min_seconds, target_seconds, overall cumulative time]
"1": [1, 2, 60, 90, 90],
"2": [2, 3, 180, 180, 270], 
"3": [5, 8, 240, 480, 750],
"4": [1, 2, 60, 120, 870]
}