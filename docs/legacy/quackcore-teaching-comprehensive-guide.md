# QuackCore Teaching Module Documentation

Welcome to the QuackCore Teaching Module documentation! This guide will help you understand and use the powerful gamified education system built into quack_core.

## Table of Contents

1. [Introduction](#introduction)
2. [Module Overview](#module-overview)
3. [Core Components](#core-components)
   - [XP System](#xp-system)
   - [Badge System](#badge-system)
   - [Quest System](#quest-system)
   - [User Progress](#user-progress)
   - [Certificates](#certificates)
4. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Basic Usage](#basic-usage)
   - [Example Workflows](#example-workflows)
5. [Core Module Deep Dive](#core-module-deep-dive)
   - [Working with User Progress](#working-with-user-progress)
   - [Managing XP](#managing-xp)
   - [Working with Badges](#working-with-badges)
   - [Working with Quests](#working-with-quests)
   - [Certificates](#working-with-certificates)
6. [Teaching NPC (Quackster)](#teaching-npc-quackster)
   - [Introduction to Quackster](#introduction-to-quackster)
   - [Integrating Quackster in Your Applications](#integrating-quackster-in-your-applications)
   - [Customizing Quackster](#customizing-quackster)
7. [Advanced Features](#advanced-features)
   - [GitHub Integration](#github-integration)
   - [LMS/Academy Features](#lmsacademy-features)
   - [Gamification Service](#gamification-service)
8. [Best Practices](#best-practices)
   - [Recommended Patterns](#recommended-patterns)
   - [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Example Projects](#example-projects)
   - [CLI Tool with Gamification](#cli-tool-with-gamification)
   - [Educational Web App](#educational-web-app)
   - [GitHub-Enhanced Learning](#github-enhanced-learning)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

## Introduction

The QuackCore Teaching Module is a gamified education system designed to make learning fun and engaging. It includes features like XP (experience points), badges, quests, and an interactive teaching NPC named Quackster. The module is designed for CLI-first interaction but can be integrated into various applications.

This teaching module is ideal for:
- Creating interactive tutorials for your applications
- Building coding challenges with gamification
- Developing educational tools with progress tracking
- Setting up mentorship systems with AI assistance
- Integrating with GitHub for collaborative learning

By the end of this documentation, you'll be comfortable using all aspects of the teaching module and ready to build engaging educational experiences for your users.

## Module Overview

The QuackCore Teaching Module consists of several interconnected components that work together to create a comprehensive educational experience:

```
quack_core.teaching
├── core - Core gamification models and services
│   ├── models.py - Data models for XP, badges, quests, etc.
│   ├── xp.py - XP management and level calculations
│   ├── badges.py - Badge definitions and management
│   ├── quests.py - Quest definitions and verification
│   ├── utils.py - Utilities for loading/saving progress
│   ├── certificates.py - Certificate generation and verification
│   └── gamification_service.py - Combined gamification services
├── npc - The Quackster teaching assistant
│   ├── agent.py - Main NPC agent orchestration
│   ├── schema.py - Data models for NPC interaction
│   ├── tools/ - Tools Quackster can use to help users
│   └── dialogue/ - Dialogue templates for Quackster
├── github - GitHub integration for teaching
│   ├── grading.py - GitHub assignment grading
│   └── teaching_service.py - GitHub teaching features
└── academy - Traditional LMS-style features
    ├── course.py - Course and module management
    ├── assignment.py - Assignment management
    ├── grading.py - Grading criteria and evaluation
    └── service.py - Teaching service interface
```

The module follows a "core + extensions" architecture:
- **Core**: The fundamental models and services for gamification
- **NPC**: Interactive teaching assistant capabilities
- **GitHub**: Integration with GitHub for assignments and grading
- **Academy**: Traditional learning management system features

You can use these components separately or together, depending on your needs.

## Core Components

### XP System

The XP (Experience Points) system is the foundation of the gamification features. Users earn XP for completing tasks, which contributes to their level and progression.

#### Key Concepts

- **XP Events**: Discrete activities or accomplishments that award XP
- **Levels**: Calculated based on accumulated XP (1 level per 100 XP by default)
- **Level-up Events**: Special events triggered when users reach new levels

#### XP Event Example

```python
from quack_core.teaching.core.models import XPEvent

# Create an XP event
code_review_event = XPEvent(
    id="code-review-123",
    label="Completed Code Review",
    points=25,
    metadata={"repo": "quackverse/quack-core", "pr_number": 42}
)
```

### Badge System

Badges are achievements that users can earn by reaching certain milestones, completing specific quests, or through other activities.

#### Key Concepts

- **Badge Types**: XP-based, quest-based, and special badges
- **Badge Requirements**: Conditions for earning badges (XP thresholds, quest completion)
- **Badge Display**: Badges have emoji representations for visual appeal

#### Badge Example

```python
from quack_core.teaching.core.models import Badge

# Define a badge
contributor_badge = Badge(
    id="first-contribution",
    name="First Contribution",
    description="Made your first contribution to the project",
    required_xp=0,  # Not XP-based
    emoji="🏆"
)
```

### Quest System

Quests are specific challenges that users can complete to earn XP and badges. They provide structure and goals for the educational journey.

#### Key Concepts

- **Quest Types**: GitHub-based, tool usage, and tutorial quests
- **Quest Verification**: Functions that check if a quest has been completed
- **Quest Rewards**: XP and optional badges awarded for completion

#### Quest Example

```python
from quack_core.teaching.core.models import Quest

# Define a quest
github_quest = Quest(
    id="star-repository",
    name="Star Repository",
    description="Star the main repository on GitHub",
    reward_xp=50,
    badge_id="github-collaborator",
    github_check={"repo": "quackverse/quack-core", "action": "star"},
)
```

### User Progress

The user progress system tracks a user's XP, completed events, quests, and earned badges across sessions.

#### Key Concepts

- **Progress Storage**: Data stored locally in the user's home directory
- **Progress Tracking**: Methods to check completion status and XP accumulation
- **GitHub Integration**: Linking progress to GitHub usernames for verification

#### User Progress Example

```python
from quack_core.teaching.core import utils

# Load user progress
user_progress = utils.load_progress()

# Check user stats
current_level = user_progress.get_level()
total_xp = user_progress.xp
next_level_xp = user_progress.get_xp_to_next_level()
```

### Certificates

The certificate system allows you to create verifiable proof of course completion or achievement.

#### Key Concepts

- **Course Completion**: Certificates are awarded for completing courses
- **Digital Verification**: Signatures ensure certificate authenticity
- **Shareable Format**: Certificates can be exported to shareable strings

#### Certificate Example

```python
from quack_core.teaching.core import certificates, utils

# Load user progress
user = utils.load_progress()

# Create a certificate if eligible
if certificates.has_earned_certificate(user, "python-basics"):
    cert = certificates.create_certificate(
        user,
        course_id="python-basics",
        additional_data={"course_name": "Python Programming Basics"}
    )
    
    # Format as markdown for display
    markdown = certificates.format_certificate_markdown(cert)
    
    # Export to shareable string
    shareable = certificates.certificate_to_string(cert)
```

## Getting Started

### Installation

The QuackCore teaching module is part of the larger QuackCore package. Install it using pip:

```bash
pip install quack-core
```

### Basic Usage

Here's a simple example of using the teaching module to track user progress:

```python
from quack_core.teaching import xp, utils
from quack_core.teaching.core.models import XPEvent

# Load user progress
user = utils.load_progress()

# Add XP for completing a task
event = XPEvent(id="used-tutorial", label="Completed Tutorial", points=10)
xp.add_xp(user, event)

# Check for new level
current_level = user.get_level()
xp_to_next = user.get_xp_to_next_level()
print(f"You are now level {current_level}! Need {xp_to_next} XP for next level.")

# Save updated progress
utils.save_progress(user)
```

### Example Workflows

#### Tracking Tutorial Completion

```python
from quack_core.teaching import xp, quests, utils
from quack_core.teaching.core.models import XPEvent

def mark_tutorial_complete(tutorial_id, tutorial_name):
    # Load user progress
    user = utils.load_progress()
    
    # Create XP event
    event = XPEvent(
        id=f"tutorial-{tutorial_id}",
        label=f"Completed Tutorial: {tutorial_name}",
        points=25
    )
    
    # Add XP
    added, old_level = xp.add_xp(user, event)
    
    # Check if tutorial completion triggers a quest
    if tutorial_id == "quickstart":
        quests.complete_quest(user, "complete-tutorial")
    
    # Save progress
    utils.save_progress(user)
    
    # Return level info
    new_level = user.get_level()
    return {
        "xp_added": 25 if added else 0,
        "level_up": new_level > old_level,
        "current_level": new_level,
        "xp_to_next": user.get_xp_to_next_level()
    }
```

#### Creating a GitHub-Connected Learning Path

```python
from quack_core.teaching import badges, quests, utils
from quack_core.teaching.core.gamification_service import GamificationService

def setup_github_learning_path(repo_name):
    # Initialize gamification service
    gamifier = GamificationService()
    
    # Create a workflow for GitHub interaction
    results = []
    
    # Step 1: Star repository
    star_result = gamifier.handle_github_star(repo_name)
    results.append(star_result)
    
    # Step 2: Automatically check for opened PR
    # (This would normally be triggered by GitHub webhook)
    # For demo, we'll simulate the user has opened a PR
    pr_result = gamifier.handle_github_pr_submission(1, repo_name)
    results.append(pr_result)
    
    # Step 3: Simulate PR merged
    merge_result = gamifier.handle_github_pr_merged(1, repo_name)
    results.append(merge_result)
    
    # Load badges earned
    user = utils.load_progress()
    earned_badges = badges.get_user_badges(user)
    
    return {
        "completed_steps": len(results),
        "total_xp_gained": sum(r.xp_added for r in results),
        "earned_badges": [b.name for b in earned_badges],
        "current_level": user.get_level()
    }
```

## Core Module Deep Dive

### Working with User Progress

The User Progress system is the central component that tracks all user achievements and metrics.

#### Loading and Saving Progress

```python
from quack_core.teaching.core import utils

# Load existing progress or create new if none exists
user = utils.load_progress()

# Make changes to user progress
user.xp += 10
user.completed_event_ids.append("new-event-id")

# Save changes
utils.save_progress(user)
```

#### Custom GitHub Username

```python
from quack_core.teaching.core import utils

# Set a custom GitHub username
user = utils.load_progress()
user.github_username = "octocat"
utils.save_progress(user)

# Later, use this username for GitHub verification
```

#### Backup and Reset

```python
from quack_core.teaching.core import utils

# Backup current progress
utils.backup_progress("before_big_change")

# Reset progress (e.g., for testing)
utils.reset_progress()

# Create new progress with default values
new_user = utils.create_new_progress()
```

### Managing XP

The XP system handles experience points, which contribute to user levels and progression.

#### Adding XP

```python
from quack_core.teaching.core import xp, utils
from quack_core.teaching.core.models import XPEvent

# Load user
user = utils.load_progress()

# Define XP event
event = XPEvent(
    id="solved-challenge",
    label="Solved Programming Challenge",
    points=15,
    metadata={"challenge_id": "fibonacci", "difficulty": "medium"}
)

# Add XP and check if this is new
is_new, old_level = xp.add_xp(user, event)

if is_new:
    print(f"Earned {event.points} XP from {event.label}!")
else:
    print("Already completed this event.")

# Check for level up
new_level = user.get_level()
if new_level > old_level:
    print(f"Leveled up to level {new_level}!")

# Save changes
utils.save_progress(user)
```

#### Quest-Based XP

```python
from quack_core.teaching.core import xp, utils

# Add XP from a completed quest
user = utils.load_progress()
xp.add_xp_from_quest(user, "github-first-pr", 100)
utils.save_progress(user)
```

#### Calculating XP Requirements

```python
from quack_core.teaching.core import utils

user = utils.load_progress()

# Get current level
level = user.get_level()

# Calculate XP needed for next level
xp_needed = user.get_xp_to_next_level()

# Display progress
total_xp = user.xp
next_level = level + 1
percentage = ((level * 100) - (xp_needed)) / (level * 100) * 100

print(f"Level {level} ({total_xp} XP)")
print(f"Progress to Level {next_level}: {percentage:.1f}%")
print(f"{xp_needed} XP needed")
```

### Working with Badges

Badges are achievements that users can earn to showcase their progress and skills.

#### Defining Badges

```python
from quack_core.teaching.core.models import Badge
from quack_core.teaching.core import badges

# Define a custom badge
custom_badge = Badge(
    id="code-ninja", 
    name="Code Ninja", 
    description="Mastered advanced coding techniques",
    required_xp=1000,  # XP-based badge
    emoji="🥷"
)

# Access pre-defined badges
all_badges = badges.get_all_badges()
github_badge = badges.get_badge("github-collaborator")
```

#### Awarding Badges

```python
from quack_core.teaching.core import badges, utils

# Load user progress
user = utils.load_progress()

# Award a badge
if badges.award_badge(user, "code-ninja"):
    print("Awarded Code Ninja badge!")
else:
    print("Badge already earned or not found.")

# Save progress
utils.save_progress(user)
```

#### Checking Badge Progress

```python
from quack_core.teaching.core import badges, utils

user = utils.load_progress()

# Check progress toward a badge
progress = badges.get_badge_progress(user, "duck-expert")
percentage = progress * 100

print(f"Progress toward Duck Expert badge: {percentage:.1f}%")

# Get next badges user could earn
next_badges = badges.get_next_badges(user, limit=3)
for badge in next_badges:
    print(f"{badge.emoji} {badge.name}: {badge.required_xp} XP required")
```

### Working with Quests

Quests are challenges that users can complete to earn XP and badges.

#### Accessing Quests

```python
from quack_core.teaching.core import quests, utils

# Get all available quests
all_quests = quests.get_all_quests()

# Get a specific quest
star_quest = quests.get_quest("star-quack-core")

# Get quests for a specific user
user = utils.load_progress()
user_quests = quests.get_user_quests(user)
completed = user_quests["completed"]
available = user_quests["available"]
```

#### Checking Quest Completion

```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()

# Check if specific quest is completed
if user.has_completed_quest("star-quack-core"):
    print("Repository already starred!")
else:
    print("Star the repository to complete this quest.")

# Check for newly completed quests
newly_completed = quests.check_quest_completion(user)
if newly_completed:
    print(f"You've completed {len(newly_completed)} new quests!")
    for quest in newly_completed:
        print(f"- {quest.name} (+{quest.reward_xp} XP)")
```

#### Completing Quests Manually

```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()

# Complete a quest (e.g., after external verification)
if quests.complete_quest(user, "run-tests", forced=True):
    print("Quest marked as complete!")
else:
    print("Quest already completed or not found.")

# Save progress
utils.save_progress(user)
```

#### Getting Quest Suggestions

```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()

# Get suggested quests for the user
suggested = quests.get_suggested_quests(user, limit=3)
print("Suggested quests:")
for quest in suggested:
    print(f"- {quest.name}: {quest.description} (+{quest.reward_xp} XP)")
```

### Working with Certificates

Certificates provide formal recognition for course completion or achievements.

#### Creating Certificates

```python
from quack_core.teaching.core import certificates, utils

user = utils.load_progress()

# Check if user is eligible for a certificate
if certificates.has_earned_certificate(user, "quackverse-basics"):
    # Create the certificate
    cert = certificates.create_certificate(
        user,
        course_id="quackverse-basics",
        issuer="QuackVerse Academy",
        additional_data={"course_name": "QuackVerse Basics", "instructor": "Dr. Duck"}
    )
    
    # Generate markdown representation
    markdown = certificates.format_certificate_markdown(cert)
    print(markdown)
    
    # Export for sharing
    shareable = certificates.certificate_to_string(cert)
    print(f"Share this certificate: {shareable}")
else:
    print("Complete all required quests to earn this certificate.")
```

#### Verifying Certificates

```python
from quack_core.teaching.core import certificates

# Parse a certificate from a shared string
cert_string = "eyJpZCI6I..."  # Received certificate string
try:
    cert = certificates.string_to_certificate(cert_string)
    
    # Verify authenticity
    if certificates.verify_certificate(cert):
        print(f"Valid certificate for {cert['course_id']} issued to {cert['recipient']}")
    else:
        print("Invalid certificate! Verification failed.")
except ValueError:
    print("Invalid certificate format.")
```

## Teaching NPC (Quackster)

### Introduction to Quackster

Quackster is an interactive teaching assistant (NPC) that helps guide users through the learning process. It can answer questions, suggest quests, verify completion, and provide tutorials.

#### Key Features

- Interactive conversational interface
- Access to user progress and achievements
- Ability to verify quest completion
- Access to tutorials and guidance
- Customizable personality and responses

### Integrating Quackster in Your Applications

#### Basic Integration

```python
from quack_core.teaching.npc import run_npc_session
from quack_core.teaching.npc.schema import TeachingNPCInput

def handle_user_query(user_text, github_username=None):
    # Create input for Quackster
    npc_input = TeachingNPCInput(
        user_input=user_text,
        github_username=github_username
    )
    
    # Run the NPC session
    response = run_npc_session(npc_input)
    
    return {
        "response": response.response_text,
        "actions": response.actions_taken,
        "suggested_quests": response.suggested_quests,
        "verify_quests": response.should_verify_quests
    }

# Example usage
result = handle_user_query("What quests can I do next?")
print(result["response"])
```

#### Maintaining Conversation Context

```python
from quack_core.teaching.npc import run_npc_session
from quack_core.teaching.npc.schema import TeachingNPCInput

class QuacksterChat:
    def __init__(self, github_username=None):
        self.github_username = github_username
        self.conversation_history = []
        
    def chat(self, user_message):
        # Create input with conversation history
        npc_input = TeachingNPCInput(
            user_input=user_message,
            github_username=self.github_username,
            conversation_context=self.conversation_history
        )
        
        # Get response
        response = run_npc_session(npc_input)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": response.response_text})
        
        # Trim history if too long
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
            
        return response

# Example usage
chatbot = QuacksterChat(github_username="octocat")
response1 = chatbot.chat("What's my current level?")
print(response1.response_text)

response2 = chatbot.chat("What should I do next?")
print(response2.response_text)
```

### Customizing Quackster

#### Custom NPC Profile

```python
import os
from quack_core.teaching.npc.schema import QuacksterProfile

# Set environment variables for customization
os.environ["QUACK_NPC_TONE"] = "enthusiastic"

# Or create a YAML file with custom profile
"""
# quackster_profile.yaml
name: "Professor Quack"
tone: "academic"
backstory: "A distinguished professor of Computer Science who enjoys quackster through practical examples"
expertise: 
  - "Python"
  - "Algorithms"
  - "Data Structures"
  - "Best Practices"
teaching_style: "Socratic method with humor"
emoji_style: "sparse"
catchphrases:
  - "Knowledge is power!"
  - "Let's code and learn!"
  - "Questions lead to understanding."
  - "Practice makes perfect!"
"""

# Then set the environment variable to point to this file
os.environ["QUACK_NPC_PROFILE"] = "~/quackster_profile.yaml"
```

#### Custom Tutorials and Content

```python
import os

# Set a custom path for tutorials
os.environ["QUACK_TUTORIAL_PATH"] = "~/my_project/tutorials"

# Create Markdown files in this directory:
"""
# python_basics.md
## Variables and Types

Python variables are created when you assign a value to them:

```python
x = 5
name = "Quackster"
```

## Control Flow

Use if statements to make decisions:

```python
if x > 10:
    print("x is greater than 10")
else:
    print("x is less than or equal to 10")
```
"""

# Now Quackster can access these tutorials when asked
```

## Advanced Features

### GitHub Integration

The QuackCore teaching module includes features for integrating with GitHub for collaborative learning, assignment management, and progress tracking.

#### Setting Up GitHub Integration

```python
from quack_core.teaching.github import create_teaching_integration

# Create the teaching integration
github_teaching = create_teaching_integration()

# Ensure repositories are starred
result = github_teaching.ensure_starred("quackverse/quackcore")
if result.success:
    print("Repository is now starred!")

# Helper for submitting assignments
def submit_assignment(forked_repo, base_repo, branch, title):
    result = github_teaching.submit_assignment(
        forked_repo=forked_repo,
        base_repo=base_repo,
        branch=branch,
        title=title,
        body="This is my submission for the assignment."
    )
    
    if result.success:
        print(f"Assignment submitted: {result.content}")
        return result.content  # PR URL
    else:
        print(f"Error: {result.error}")
        return None
```

#### Automated Grading

```python
from quack_core.teaching.github import create_teaching_integration

def grade_submission(repo, pr_number):
    github_teaching = create_teaching_integration()
    
    # Define grading criteria
    criteria = {
        "passing_threshold": 0.7,
        "required_files": {
            "points": 50,
            "files": ["GET-STARTED.md", "main.py", "test_main.py"]
        },
        "required_changes": {
            "points": 30,
            "changes": [
                {
                    "file": "main.py",
                    "min_additions": 10,
                    "description": "Implement the main function"
                }
            ]
        },
        "prohibited_patterns": {
            "points": 20,
            "patterns": [
                {
                    "pattern": r"import os\s*;",
                    "description": "Using semicolons in Python is discouraged"
                }
            ]
        }
    }
    
    # Run the grading
    result = github_teaching.grade_submission_by_number(
        repo=repo,
        pr_number=pr_number,
        grading_criteria=criteria
    )
    
    if result.success:
        grade = result.content
        print(f"Score: {grade.score * 100:.1f}%")
        print(f"Passed: {grade.passed}")
        print(f"Feedback: {grade.comments}")
        return grade
    else:
        print(f"Error: {result.error}")
        return None
```

### LMS/Academy Features

The academy module provides traditional Learning Management System (LMS) features for course management, assignments, and grading.

#### Setting Up a Course

```python
from quack_core.teaching.academy import service
from quack_core.teaching.academy import Course, CourseModule, ModuleItem, ItemType

# Initialize the quackster service
service.initialize()

# Create a new course context
result = service.create_context(
    course_name="Python Programming 101",
    github_org="my-org"
)

if result.success:
    # Create a course with modules
    course = Course.create(
        name="Python Programming 101",
        code="PY101",
        description="Introduction to Python programming",
        instructors=["dr_duck"]
    )
    
    # Add modules
    intro_module = CourseModule.create(
        title="Introduction to Python",
        description="Basic Python concepts and setup",
        position=0
    )
    
    # Add items to module
    intro_module.add_item(
        ModuleItem.create(
            title="Installing Python",
            type=ItemType.LECTURE,
            description="Learn how to install Python on your system"
        )
    )
    
    intro_module.add_item(
        ModuleItem.create(
            title="First Python Program",
            type=ItemType.ASSIGNMENT,
            description="Write your first Python program",
            points=10.0
        )
    )
    
    # Add module to course
    course.add_module(intro_module)
    
    # Save the course configuration
    # (In a real implementation, you would save this to a file or database)
```

#### Managing Assignments

```python
from quack_core.teaching.academy import service
from quack_core.teaching.academy import Assignment, AssignmentType, AssignmentStatus

# Create an assignment
assignment = Assignment.create(
    name="Data Structure Implementation",
    description="Implement a linked list in Python",
    assignment_type=AssignmentType.INDIVIDUAL,
    points=100.0
)

# Publish the assignment
assignment.publish()

# Create repositories for students from a template
result = service.create_assignment_from_template(
    assignment_name="data-structures",
    template_repo="python-class/linked-list-template",
    description="Implement a linked list in Python",
    due_date="2023-12-01T23:59:59",
    students=["student1", "student2", "student3"]
)

if result.success:
    print(f"Created {len(result.repositories)} assignment repositories")
else:
    print(f"Error: {result.error}")
```

#### Grading Student Work

```python
from quack_core.teaching.academy.grading import GradingCriteria, GradingCriterion, GradeResult

# Define grading criteria
criteria = GradingCriteria.create(
    name="Linked List Implementation",
    assignment_id="linked-list",
    passing_threshold=0.7
)

# Add specific criteria
criteria.add_criterion(
    GradingCriterion.create(
        name="Implementation",
        points=50.0,
        description="Correct implementation of linked list _ops",
        required=True
    )
)

criteria.add_criterion(
    GradingCriterion.create(
        name="Testing",
        points=25.0,
        description="Comprehensive test cases"
    )
)

criteria.add_criterion(
    GradingCriterion.create(
        name="Documentation",
        points=25.0,
        description="Clear and complete documentation"
    )
)

# Create a grade result
grade = GradeResult.create(
    submission_id="student1-linked-list",
    student_id="student1",
    assignment_id="linked-list",
    score=85.0,
    max_points=100.0,
    passed=True,
    criterion_scores={
        "Implementation": 40.0,
        "Testing": 20.0,
        "Documentation": 25.0
    },
    comments="Good work overall. Implementation could be more efficient."
)

# Format for feedback
feedback_text = grade.format_for_feedback()

# Update gamification based on grade
grade.update_gamification()
```

### Gamification Service

The Gamification Service integrates all teaching components to provide a unified system for tracking progress and awarding achievements.

#### Basic Usage

```python
from quack_core.teaching.core.gamification_service import GamificationService

# Create service instance (loads user progress automatically)
service = GamificationService()

# Handle an XP event
event_result = service.handle_event(
    XPEvent(
        id="code-review-complete",
        label="Completed Code Review",
        points=25
    )
)

print(event_result.message)  # Displays achievement message

# The service automatically:
# - Adds XP from the event
# - Checks for level ups
# - Checks for newly completed quests
# - Checks for newly earned badges
```

#### Handling Multiple Events

```python
from quack_core.teaching.core.gamification_service import GamificationService
from quack_core.teaching.core.models import XPEvent

def track_project_completion(user_project):
    # Create service
    gamifier = GamificationService()
    
    # Create multiple XP events
    events = [
        XPEvent(
            id=f"project-planning-{user_project.id}",
            label="Completed Project Planning",
            points=10,
            metadata={"project_id": user_project.id, "phase": "planning"}
        ),
        XPEvent(
            id=f"project-implementation-{user_project.id}",
            label="Completed Implementation",
            points=30,
            metadata={"project_id": user_project.id, "phase": "implementation"}
        ),
        XPEvent(
            id=f"project-testing-{user_project.id}",
            label="Completed Testing",
            points=20,
            metadata={"project_id": user_project.id, "phase": "testing"}
        )
    ]
    
    # Handle all events together
    result = gamifier.handle_events(events)
    
    return {
        "xp_gained": result.xp_added,
        "level_up": result.level_up,
        "new_level": result.level,
        "completed_quests": result.completed_quests,
        "earned_badges": result.earned_badges,
        "message": result.message
    }
```

#### Handling GitHub Interactions

```python
from quack_core.teaching.core.gamification_service import GamificationService

def handle_github_workflow(repo, pr_number, action):
    # Create service
    gamifier = GamificationService()
    
    if action == "star":
        # Handle repository star
        result = gamifier.handle_github_star(repo)
    elif action == "submit_pr":
        # Handle PR submission
        result = gamifier.handle_github_pr_submission(pr_number, repo)
    elif action == "merge_pr":
        # Handle PR merge
        result = gamifier.handle_github_pr_merged(pr_number, repo)
    else:
        return {"success": False, "message": "Unknown action"}
    
    return {
        "success": True,
        "xp_gained": result.xp_added,
        "level_up": result.level_up,
        "completed_quests": result.completed_quests,
        "earned_badges": result.earned_badges,
        "message": result.message
    }
```

#### Course and Learning Integrations

```python
from quack_core.teaching.core.gamification_service import GamificationService

def track_learning_progress(course_id, module_id=None, assignment_id=None):
    # Create service
    gamifier = GamificationService()
    
    if module_id:
        # Record module completion
        result = gamifier.handle_module_completion(
            course_id=course_id,
            module_id=module_id,
            module_name=f"Module {module_id}"
        )
    elif assignment_id:
        # Record assignment completion (with score)
        result = gamifier.handle_assignment_completion(
            assignment_id=assignment_id,
            assignment_name=f"Assignment {assignment_id}",
            score=90.0,
            max_score=100.0
        )
    else:
        # Record full course completion
        result = gamifier.handle_course_completion(
            course_id=course_id,
            course_name=f"Course {course_id}"
        )
    
    return {
        "xp_gained": result.xp_added,
        "level_up": result.level_up,
        "new_level": result.level,
        "completed_quests": result.completed_quests,
        "earned_badges": result.earned_badges,
        "message": result.message
    }
```

## Best Practices

### Recommended Patterns

#### Event-Based Tracking

Track user actions as discrete events with unique IDs to avoid duplicate XP awards:

```python
from quack_core.teaching.core.models import XPEvent

# Generate a unique event ID based on user and action
def create_unique_event(user_id, action, item_id=None):
    if item_id:
        event_id = f"{action}-{item_id}-{user_id}"
    else:
        event_id = f"{action}-{user_id}"
        
    return XPEvent(
        id=event_id,
        label=f"User {user_id} performed {action}",
        points=get_points_for_action(action),
        metadata={"user_id": user_id, "action": action, "item_id": item_id}
    )
```

#### Progress Display Helpers

Create consistent display methods for progress information:

```python
def format_progress_bar(current, maximum, length=20):
    """Create a text-based progress bar."""
    filled = int(length * (current / maximum))
    bar = '█' * filled + '░' * (length - filled)
    percentage = current / maximum * 100
    return f"[{bar}] {percentage:.1f}%"

def format_user_progress(user):
    """Format user's progress information."""
    level = user.get_level()
    xp = user.xp
    next_level = level + 1
    xp_required = next_level * 100
    xp_have = xp - ((level - 1) * 100)
    xp_needed = xp_required - xp_have
    
    return {
        "level": level,
        "xp": xp,
        "xp_needed": xp_needed,
        "progress_bar": format_progress_bar(xp_have, 100),
        "badge_count": len(user.earned_badge_ids),
        "quest_count": len(user.completed_quest_ids),
        "displayable": f"Level {level} ({xp} XP)\n{format_progress_bar(xp_have, 100)}\n{xp_needed} XP needed for Level {next_level}"
    }
```

#### Consistent Notification System

Create a uniform way to communicate achievements to users:

```python
class AchievementNotifier:
    """Handle achievement notifications consistently."""
    
    def __init__(self, notify_func=print):
        self.notify_func = notify_func
        
    def notify_xp(self, event, is_new):
        """Notify about XP earned."""
        if is_new:
            self.notify_func(f"🎯 Earned {event.points} XP from {event.label}")
            
    def notify_level_up(self, old_level, new_level):
        """Notify about level up."""
        self.notify_func(f"🎆 Level Up! You advanced from level {old_level} to level {new_level}!")
        
    def notify_badge(self, badge):
        """Notify about badge earned."""
        self.notify_func(f"🏆 Badge Unlocked: {badge.emoji} {badge.name} - {badge.description}")
        
    def notify_quest(self, quest):
        """Notify about quest completed."""
        self.notify_func(f"✅ Quest Completed: {quest.name} (+{quest.reward_xp} XP)")
        
    def handle_gamification_result(self, result):
        """Process a GamificationResult and generate appropriate notifications."""
        if result.xp_added > 0:
            self.notify_func(f"🎯 Earned {result.xp_added} XP")
            
        if result.level_up:
            self.notify_func(f"🎆 Level Up! You advanced to level {result.level}!")
            
        for quest_id in result.completed_quests:
            quest = quests.get_quest(quest_id)
            if quest:
                self.notify_quest(quest)
                
        for badge_id in result.earned_badges:
            badge = badges.get_badge(badge_id)
            if badge:
                self.notify_badge(badge)
                
        if result.message:
            self.notify_func(result.message)
```

#### Periodic Progress Check

Schedule regular checks for quest completion and updates:

```python
def periodic_progress_check():
    """Perform a periodic check for quest completion and updates."""
    # Load user progress
    user = utils.load_progress()
    
    # Check for completed quests
    newly_completed = quests.check_quest_completion(user)
    
    # Apply completed quests
    for quest in newly_completed:
        quests.complete_quest(user, quest.id)
        print(f"Quest completed: {quest.name}")
    
    # Check for badge eligibility
    user_badges = badges.get_user_badges(user)
    next_badges = badges.get_next_badges(user)
    
    if next_badges:
        closest_badge = next_badges[0]
        progress = badges.get_badge_progress(user, closest_badge.id)
        print(f"Next badge: {closest_badge.name} - {progress*100:.1f}% complete")
    
    # Save updated progress
    utils.save_progress(user)
    
    return {
        "quests_completed": [q.id for q in newly_completed],
        "badge_count": len(user_badges),
        "next_badge_progress": progress if next_badges else 0
    }
```

### Anti-Patterns to Avoid

#### 1. Direct Manipulation of XP

**Bad Practice**:
```python
# DON'T DO THIS
user = utils.load_progress()
user.xp += 50  # Directly manipulating XP
utils.save_progress(user)
```

**Good Practice**:
```python
# DO THIS INSTEAD
from quack_core.teaching.core.models import XPEvent
from quack_core.teaching.core import xp, utils

user = utils.load_progress()
event = XPEvent(id="unique-event-id", label="Descriptive Label", points=50)
xp.add_xp(user, event)
utils.save_progress(user)
```

#### 2. Ignoring Idempotency

**Bad Practice**:
```python
# DON'T DO THIS
def award_points_for_login():
    user = utils.load_progress()
    # This doesn't check if points were already awarded today
    event = XPEvent(id="daily-login", label="Daily Login", points=5)
    xp.add_xp(user, event)
    utils.save_progress(user)
```

**Good Practice**:
```python
# DO THIS INSTEAD
from datetime import datetime

def award_points_for_login():
    user = utils.load_progress()
    today = datetime.now().strftime("%Y-%m-%d")
    event_id = f"daily-login-{today}"
    
    # Check if already awarded today
    if not user.has_completed_event(event_id):
        event = XPEvent(id=event_id, label="Daily Login", points=5)
        xp.add_xp(user, event)
        utils.save_progress(user)
        return True
    return False
```

#### 3. Ignoring GitHub Username

**Bad Practice**:
```python
# DON'T DO THIS
def verify_github_actions():
    user = utils.load_progress()
    # This doesn't check if GitHub username is set
    quests.apply_completed_quests(user)
    utils.save_progress(user)
```

**Good Practice**:
```python
# DO THIS INSTEAD
def verify_github_actions():
    user = utils.load_progress()
    
    if not user.github_username:
        print("GitHub username not set. Please set it to track GitHub quests.")
        return False
        
    quests.apply_completed_quests(user)
    utils.save_progress(user)
    return True
```

#### 4. Not Using the Gamification Service

**Bad Practice**:
```python
# DON'T DO THIS - Manual orchestration is error-prone
def handle_course_completion(user, course_id):
    # Manual XP award
    event = XPEvent(id=f"course-{course_id}", label=f"Completed Course {course_id}", points=100)
    xp.add_xp(user, event)
    
    # Manual badge check
    if not user.has_earned_badge("duck-graduate"):
        badges.award_badge(user, "duck-graduate")
        
    # Save progress
    utils.save_progress(user)
```

**Good Practice**:
```python
# DO THIS INSTEAD - Use the integrated service
from quack_core.teaching.core.gamification_service import GamificationService

def handle_course_completion(course_id, course_name):
    service = GamificationService()
    result = service.handle_course_completion(course_id, course_name)
    
    if result.message:
        print(result.message)
        
    return result
```

#### 5. Loading Progress Multiple Times

**Bad Practice**:
```python
# DON'T DO THIS - Inefficient and can lead to data loss
def update_user_stats(user_id, completed_quest):
    # Load user progress
    user = utils.load_progress()
    
    # Update XP
    event = XPEvent(id=f"quest-{completed_quest}", label=f"Completed Quest", points=50)
    xp.add_xp(user, event)
    utils.save_progress(user)
    
    # Load again in another function (data race potential)
    user = utils.load_progress()
    quests.complete_quest(user, completed_quest)
    utils.save_progress(user)
```

**Good Practice**:
```python
# DO THIS INSTEAD - Load once, make all changes, save once
def update_user_stats(user_id, completed_quest):
    # Load user progress once
    user = utils.load_progress()
    
    # Make all updates
    event = XPEvent(id=f"quest-{completed_quest}", label=f"Completed Quest", points=50)
    xp.add_xp(user, event)
    quests.complete_quest(user, completed_quest)
    
    # Save once at the end
    utils.save_progress(user)
```

## Example Projects

### CLI Tool with Gamification

Here's how you might implement a CLI tool that includes gamification:

```python
import argparse
import sys

from quack_core.teaching import xp, utils, badges, quests
from quack_core.teaching.core.models import XPEvent
from quack_core.teaching.core.gamification_service import GamificationService

def main():
    parser = argparse.ArgumentParser(description="MyCoolTool - Now with gamification!")
    parser.add_argument("command", choices=["run", "status", "help"])
    parser.add_argument("--args", help="Arguments for the command")
    
    args = parser.parse_args()
    
    if args.command == "help":
        show_help()
        return
        
    elif args.command == "status":
        show_status()
        return
        
    elif args.command == "run":
        run_tool(args.args)
        return
        
def show_help():
    print("MyCoolTool Help")
    print("Commands:")
    print("  run    - Run the main tool")
    print("  status - Show your progress and achievements")
    print("  help   - Show this help message")
    
def show_status():
    # Load user progress
    user = utils.load_progress()
    
    # Calculate status information
    level = user.get_level()
    xp = user.xp
    next_level = level + 1
    xp_needed = user.get_xp_to_next_level()
    
    # Get badges and quests
    user_badges = badges.get_user_badges(user)
    completed_quests = len(user.completed_quest_ids)
    
    # Display status
    print(f"=== MyCoolTool User Status ===")
    print(f"Level: {level} ({xp} XP)")
    print(f"XP needed for next level: {xp_needed}")
    print(f"Badges earned: {len(user_badges)}")
    print(f"Quests completed: {completed_quests}")
    
    if user_badges:
        print("\nYour badges:")
        for badge in user_badges:
            print(f"  {badge.emoji} {badge.name} - {badge.description}")
            
    # Suggest next quests
    suggested = quests.get_suggested_quests(user, limit=3)
    if suggested:
        print("\nSuggested quests:")
        for quest in suggested:
            print(f"  - {quest.name}: {quest.description}")
            
def run_tool(tool_args):
    # Your actual tool functionality here
    print(f"Running tool with args: {tool_args}")
    
    # Then add gamification
    gamifier = GamificationService()
    
    # Track tool usage
    result = gamifier.handle_tool_usage("MyCoolTool", "run")
    
    # Check for quest completion
    quests_completed = result.completed_quests
    if quests_completed:
        print("\n🎉 Quest Completed! 🎉")
        for quest_id in quests_completed:
            quest = quests.get_quest(quest_id)
            if quest:
                print(f"✅ {quest.name}: +{quest.reward_xp} XP")
    
    # Display badges earned            
    badges_earned = result.earned_badges
    if badges_earned:
        print("\n🏆 Badge Earned! 🏆")
        for badge_id in badges_earned:
            badge = badges.get_badge(badge_id)
            if badge:
                print(f"{badge.emoji} {badge.name} - {badge.description}")
    
    # Show level up
    if result.level_up:
        print(f"\n🎆 LEVEL UP! 🎆")
        print(f"You are now level {result.level}!")
        
    # Get status after changes
    user = utils.load_progress()
    print(f"\nCurrent level: {user.get_level()} ({user.xp} XP)")
    print(f"XP needed for next level: {user.get_xp_to_next_level()}")

if __name__ == "__main__":
    main()
```

### Educational Web App

Here's an example of how to integrate the teaching module into a web application:

```python
from flask import Flask, request, jsonify, session
from quack_core.teaching.core.gamification_service import GamificationService
from quack_core.teaching.npc import run_npc_session
from quack_core.teaching.npc.schema import TeachingNPCInput
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Store conversation history per user
conversation_histories = {}

@app.route('/api/progress', methods=['GET'])
def get_progress():
    # Get github username from session
    github_username = session.get('github_username')
    
    # Create gamification service
    gamifier = GamificationService()
    
    # Get user progress
    user = gamifier.progress
    
    # Return progress data
    return jsonify({
        'level': user.get_level(),
        'xp': user.xp,
        'xp_needed': user.get_xp_to_next_level(),
        'badges': [
            {'id': badge_id, 'name': badge.name, 'emoji': badge.emoji}
            for badge_id in user.earned_badge_ids
            if (badge := gamifier._get_badge(badge_id))
        ],
        'quests_completed': len(user.completed_quest_ids),
    })

@app.route('/api/complete-tutorial', methods=['POST'])
def complete_tutorial():
    # Get data from request
    data = request.json
    tutorial_id = data.get('tutorial_id')
    tutorial_name = data.get('tutorial_name')
    
    # Create gamification service
    gamifier = GamificationService()
    
    # Add XP for tutorial completion
    result = gamifier.handle_event(
        XPEvent(
            id=f"tutorial-{tutorial_id}",
            label=f"Completed Tutorial: {tutorial_name}",
            points=25
        )
    )
    
    # Return result
    return jsonify({
        'success': True,
        'message': result.message,
        'xp_added': result.xp_added,
        'level_up': result.level_up,
        'new_level': result.level,
        'quests_completed': result.completed_quests,
        'badges_earned': result.earned_badges
    })

@app.route('/api/quackster', methods=['POST'])
def chat_with_quackster():
    # Get data from request
    data = request.json
    user_input = data.get('message')
    github_username = session.get('github_username')
    
    # Get conversation history for this user
    user_id = session.get('user_id', 'default_user')
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    
    # Create input for Quackster
    npc_input = TeachingNPCInput(
        user_input=user_input,
        github_username=github_username,
        conversation_context=conversation_histories[user_id]
    )
    
    # Run the NPC session
    response = run_npc_session(npc_input)
    
    # Update conversation history
    conversation_histories[user_id].append({"role": "user", "content": user_input})
    conversation_histories[user_id].append({"role": "assistant", "content": response.response_text})
    
    # Trim history if too long
    if len(conversation_histories[user_id]) > 10:
        conversation_histories[user_id] = conversation_histories[user_id][-10:]
    
    # Return response
    return jsonify({
        'response': response.response_text,
        'actions': response.actions_taken,
        'suggested_quests': response.suggested_quests,
        'should_verify': response.should_verify_quests
    })

@app.route('/api/verify-quests', methods=['POST'])
def verify_quests():
    # Create gamification service
    gamifier = GamificationService()
    
    # Check for completed quests
    user = gamifier.progress
    newly_completed = quests.check_quest_completion(user)
    
    # Apply completed quests
    results = []
    for quest in newly_completed:
        result = gamifier.complete_quest(quest.id)
        results.append({
            'quest_id': quest.id,
            'quest_name': quest.name,
            'xp_awarded': quest.reward_xp,
            'badge_awarded': quest.badge_id
        })
    
    return jsonify({
        'success': True,
        'quests_completed': results
    })

@app.route('/api/set-github', methods=['POST'])
def set_github():
    # Get data from request
    data = request.json
    github_username = data.get('github_username')
    
    # Store in session
    session['github_username'] = github_username
    
    # Update user progress
    gamifier = GamificationService()
    gamifier.progress.github_username = github_username
    gamifier.save()
    
    return jsonify({
        'success': True,
        'message': f'GitHub username set to {github_username}'
    })

if __name__ == '__main__':
    app.run(debug=True)
```

### GitHub-Enhanced Learning

Here's how to build a learning system that integrates with GitHub:

```python
from quack_core.teaching.github import create_teaching_integration
from quack_core.teaching.core.gamification_service import GamificationService
import time

class GitHubLearningProgram:
    def __init__(self, github_username):
        self.github_username = github_username
        self.github_teaching = create_teaching_integration()
        self.gamifier = GamificationService()
        
        # Set GitHub username in progress
        self.gamifier.progress.github_username = github_username
        self.gamifier.save()
        
    def start_program(self):
        """Initialize the learning program."""
        print(f"Welcome to the GitHub Learning Program, {self.github_username}!")
        print("This program will guide you through becoming a GitHub contributor.")
        print("Complete the following steps to earn badges and level up!")
        
        # Display initial status
        self.show_status()
        
    def show_status(self):
        """Show current user status."""
        user = self.gamifier.progress
        level = user.get_level()
        xp = user.xp
        
        print(f"\n=== Current Status ===")
        print(f"Level: {level} ({xp} XP)")
        print(f"XP needed for next level: {user.get_xp_to_next_level()}")
        print(f"Badges earned: {len(user.earned_badge_ids)}")
        print(f"Quests completed: {len(user.completed_quest_ids)}")
        
        # Show next steps based on quests
        self.show_next_steps()
        
    def show_next_steps(self):
        """Show next steps based on completed quests."""
        user = self.gamifier.progress
        
        # Define steps in the program
        steps = [
            {
                "quest_id": "star-quack-core",
                "description": "Star the QuackCore repository",
                "instructions": "Go to https://github.com/quackverse/quackcore and click the star button",
                "verification": lambda: self.github_teaching.ensure_starred("quackverse/quack-core")
            },
            {
                "quest_id": "open-pr",
                "description": "Open your first Pull Request",
                "instructions": "Fork the repository, make a change, and open a Pull Request",
                "verification": None  # This is detected automatically via GitHub events
            },
            {
                "quest_id": "merged-pr",
                "description": "Get your Pull Request merged",
                "instructions": "Work with maintainers to get your PR approved and merged",
                "verification": None  # This is detected automatically via GitHub events
            }
        ]
        
        # Find the first incomplete step
        next_step = None
        for step in steps:
            if not user.has_completed_quest(step["quest_id"]):
                next_step = step
                break
                
        if next_step:
            print("\n=== Next Step ===")
            print(f"{next_step['description']}")
            print(f"Instructions: {next_step['instructions']}")
            
            # If verification is available, offer to check
            if next_step["verification"]:
                check = input("Would you like to verify this step now? (y/n): ")
                if check.lower() == 'y':
                    self.verify_step(next_step)
        else:
            print("\n🎉 Congratulations! You've completed all steps in the program!")
            
    def verify_step(self, step):
        """Verify a step using its verification function."""
        print(f"Verifying: {step['description']}...")
        
        # Run the verification function
        if step["verification"]:
            result = step["verification"]()
            
            if result.success:
                print(f"✅ Verified! You've completed this step.")
                
                # Check for new quests and badges
                self.check_progress_updates()
            else:
                print(f"❌ Not yet completed. {result.error}")
                
        time.sleep(1)  # Small delay to avoid rate limiting
        
    def check_progress_updates(self):
        """Check for quest completions and badge awards."""
        # Verify quest completion
        user = self.gamifier.progress
        newly_completed = quests.check_quest_completion(user)
        
        # Apply completed quests
        for quest in newly_completed:
            result = self.gamifier.complete_quest(quest.id)
            print(f"\n🎉 Quest Completed: {quest.name} (+{quest.reward_xp} XP)")
            
            if result.earned_badges:
                for badge_id in result.earned_badges:
                    badge = badges.get_badge(badge_id)
                    if badge:
                        print(f"🏆 Badge Earned: {badge.emoji} {badge.name}")
                        
            if result.level_up:
                print(f"🎆 LEVEL UP! You're now level {result.level}!")
                
        # Show updated status
        self.show_status()
        
    def run_interactive(self):
        """Run an interactive session of the learning program."""
        self.start_program()
        
        while True:
            print("\n=== Menu ===")
            print("1. Show current status")
            print("2. Show next steps")
            print("3. Verify progress")
            print("4. Exit")
            
            choice = input("Select an option (1-4): ")
            
            if choice == '1':
                self.show_status()
            elif choice == '2':
                self.show_next_steps()
            elif choice == '3':
                self.check_progress_updates()
            elif choice == '4':
                print("Thank you for using the GitHub Learning Program!")
                break
            else:
                print("Invalid option. Please try again.")

# Example usage
if __name__ == "__main__":
    github_username = input("Enter your GitHub username: ")
    program = GitHubLearningProgram(github_username)
    program.run_interactive()
```

## Troubleshooting

### Common Issues and Solutions

#### 1. XP Not Being Awarded

**Issue**: You've created an XP event, but the user's XP isn't increasing.

**Solution**:
- Check if the event ID is unique. The system prevents duplicate XP awards for the same event ID.
- Verify that `utils.save_progress(user)` is called after adding XP.
- Check that the event ID isn't already in the user's `completed_event_ids` list.

```python
# Check if event already completed
if not user.has_completed_event("event-id"):
    # It's a new event, add XP
    event = XPEvent(id="event-id", label="Event Label", points=10)
    xp.add_xp(user, event)
    utils.save_progress(user)
else:
    print("Event already completed")
```

#### 2. GitHub Verification Not Working

**Issue**: GitHub-based quests aren't being properly verified.

**Solution**:
- Ensure the user has a GitHub username set: `user.github_username`
- Check the GitHub integration is properly initialized
- Verify the quest has the correct `github_check` parameters
- Try manually completing the quest to see if it works

```python
# Debug GitHub verification issues
from quack_core.teaching.core import github_api

# Check if GitHub integration is working
if not github_api._get_github_client():
    print("GitHub client not available")
    
# Test GitHub _ops directly
user = utils.load_progress()
if user.github_username:
    has_starred = github_api.has_starred_repo(user.github_username, "quackverse/quack-core")
    print(f"Has starred repository: {has_starred}")
    
    has_pr = github_api.has_opened_pr(user.github_username, "quackverse")
    print(f"Has opened PR: {has_pr}")
else:
    print("GitHub username not set")
```

#### 3. Quests Not Completing Automatically

**Issue**: You've completed quest requirements, but quests aren't being marked as complete.

**Solution**:
- Ensure you're calling `quests.apply_completed_quests(user)` to check and apply new completions
- Verify the quest has a proper `verify_func` implementation
- Check that quest requirements are properly met
- Try manually completing the quest for testing

```python
# Debug quest completion
from quack_core.teaching.core import quests, utils

user = utils.load_progress()

# Get a specific quest
quest = quests.get_quest("quest-id")
if quest and quest.verify_func:
    # Test the verification function directly
    result = quest.verify_func(user)
    print(f"Quest verification result: {result}")
    
    # If verification passes but quest isn't completing,
    # try manual completion
    if result and not user.has_completed_quest(quest.id):
        quests.complete_quest(user, quest.id)
        utils.save_progress(user)
        print("Manually completed quest")
```

#### 4. NPC (Quackster) Not Responding Correctly

**Issue**: The Quackster NPC isn't giving expected responses or is giving errors.

**Solution**:
- Check that the LLM integration is properly configured
- Verify that user memory is being updated
- Try resetting the conversation history
- Check if tools are being executed correctly

```python
from quack_core.teaching.npc import run_npc_session
from quack_core.teaching.npc.schema import TeachingNPCInput
from quack_core.teaching.npc import memory

# Debug NPC responses
def debug_npc_response(user_input):
    # Get user memory
    user_memory = memory.get_user_memory()
    
    # Create minimal input
    npc_input = TeachingNPCInput(
        user_input=user_input,
        github_username=user_memory.github_username,
        conversation_context=[]  # Empty to remove history issues
    )
    
    # Try to get response
    try:
        response = run_npc_session(npc_input)
        print(f"Response: {response.response_text}")
        print(f"Actions: {response.actions_taken}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
```

#### 5. Progress Not Saving

**Issue**: User progress changes aren't being saved between sessions.

**Solution**:
- Make sure you're calling `utils.save_progress(user)` after making changes
- Check if the user has permissions to write to the save location
- Verify the correct data directory is being used
- Try saving to a custom location for testing

```python
import os
from quack_core.teaching.core import utils

# Debug progress saving
def verify_progress_saving():
    # Get the data directory path
    data_dir = utils.get_user_data_dir()
    print(f"Data directory: {data_dir}")
    
    # Check if directory exists and is writable
    if not os.path.exists(data_dir):
        print(f"Directory doesn't exist. Creating...")
        try:
            os.makedirs(data_dir, exist_ok=True)
            print("Directory created successfully")
        except Exception as e:
            print(f"Error creating directory: {e}")
            return False
    
    # Check write permissions
    if not os.access(data_dir, os.W_OK):
        print("No write permission to data directory")
        return False
        
    # Test saving
    user = utils.load_progress()
    original_xp = user.xp
    
    # Make a change
    user.xp += 1
    
    # Try to save
    if utils.save_progress(user):
        print("Progress saved successfully")
        
        # Reload to verify
        reloaded = utils.load_progress()
        if reloaded.xp == original_xp + 1:
            print("Verified: Changes were saved correctly")
            
            # Restore original value
            reloaded.xp = original_xp
            utils.save_progress(reloaded)
            return True
        else:
            print("Error: Changes were not saved correctly")
            return False
    else:
        print("Error saving progress")
        return False
```

## API Reference

### Core Models

#### XPEvent

Represents an activity or accomplishment that awards XP to a user.

**Fields**:
- `id`: Unique identifier for the event
- `label`: Human-readable label for the event
- `points`: Number of XP points this event awards
- `metadata`: Additional metadata about the event (optional)

**Example**:
```python
from quack_core.teaching.core.models import XPEvent

event = XPEvent(
    id="complete-tutorial-123",
    label="Completed Python Basics Tutorial",
    points=25,
    metadata={"tutorial_id": "py-basics", "difficulty": "beginner"}
)
```

#### Badge

Represents an achievement that can be earned by a user.

**Fields**:
- `id`: Unique identifier for the badge
- `name`: Display name of the badge
- `description`: Description of what the badge represents
- `required_xp`: XP threshold required to earn this badge
- `emoji`: Emoji representing this badge

**Example**:
```python
from quack_core.teaching.core.models import Badge

badge = Badge(
    id="python-master",
    name="Python Master",
    description="Achieved mastery of Python programming",
    required_xp=1000,
    emoji="🐍"
)
```

#### Quest

Represents a specific challenge that users can complete to earn XP and badges.

**Fields**:
- `id`: Unique identifier for the quest
- `name`: Display name of the quest
- `description`: Description of what the quest involves
- `reward_xp`: Amount of XP awarded for completing this quest
- `badge_id`: ID of the badge awarded for completing this quest (optional)
- `github_check`: GitHub check parameters (optional)
- `verify_func`: Function to verify if this quest is completed (optional)

**Example**:
```python
from quack_core.teaching.core.models import Quest

quest = Quest(
    id="first-python-program",
    name="First Python Program",
    description="Write and run your first Python program",
    reward_xp=50,
    badge_id="python-initiate",
    github_check=None
)

# Define a verification function
def verify_first_python(user_progress):
    return "run-python" in user_progress.completed_event_ids

# Assign the verification function
quest.verify_func = verify_first_python
```

#### UserProgress

Tracks a user's XP, completed events, quests, and earned badges.

**Fields**:
- `github_username`: GitHub username of the user (optional)
- `completed_event_ids`: IDs of XP events the user has completed
- `completed_quest_ids`: IDs of quests the user has completed
- `earned_badge_ids`: IDs of badges the user has earned
- `xp`: Total XP points earned by the user

**Methods**:
- `has_completed_event(event_id)`: Check if the user has completed a specific XP event
- `has_completed_quest(quest_id)`: Check if the user has completed a specific quest
- `has_earned_badge(badge_id)`: Check if the user has earned a specific badge
- `get_level()`: Calculate the user's current level based on XP
- `get_xp_to_next_level()`: Calculate XP needed to reach the next level

**Example**:
```python
from quack_core.teaching.core import utils

# Load progress
user = utils.load_progress()

# Check completion status
if user.has_completed_quest("star-quack-core"):
    print("QuackCore repository already starred!")
else:
    print("Star the QuackCore repository to complete this quest.")

# Check level and XP
level = user.get_level()
xp = user.xp
xp_needed = user.get_xp_to_next_level()
print(f"Level {level} ({xp} XP) - {xp_needed} XP needed for next level")
```

### Core Functions

#### XP Management

**`xp.add_xp(user, event)`**  
Add XP to a user from an XP event.

**Parameters**:
- `user`: The UserProgress instance to add XP to
- `event`: The XPEvent providing the points

**Returns**:
- Tuple of (is_new_event, level_before)

**Example**:
```python
from quack_core.teaching.core import xp, utils
from quack_core.teaching.core.models import XPEvent

user = utils.load_progress()
event = XPEvent(id="unique-id", label="Event Description", points=25)
is_new, old_level = xp.add_xp(user, event)

if is_new:
    print(f"Awarded {event.points} XP!")
    
    # Check for level up
    new_level = user.get_level()
    if new_level > old_level:
        print(f"Level up! Now level {new_level}")
        
    utils.save_progress(user)
else:
    print("Already completed this event")
```

**`xp.add_xp_from_quest(user, quest_id, xp_amount)`**  
Add XP to a user from completing a quest.

**Parameters**:
- `user`: The UserProgress instance to add XP to
- `quest_id`: ID of the completed quest
- `xp_amount`: Amount of XP to award

**Example**:
```python
from quack_core.teaching.core import xp, utils

user = utils.load_progress()
xp.add_xp_from_quest(user, "star-quack-core", 50)
utils.save_progress(user)
```

#### Badge Management

**`badges.get_all_badges()`**  
Get all available badges.

**Returns**:
- List of all badge definitions

**Example**:
```python
from quack_core.teaching.core import badges

all_badges = badges.get_all_badges()
print(f"Total badges available: {len(all_badges)}")
```

**`badges.get_badge(badge_id)`**  
Get a specific badge by ID.

**Parameters**:
- `badge_id`: ID of the badge to retrieve

**Returns**:
- Badge if found, None otherwise

**Example**:
```python
from quack_core.teaching.core import badges

badge = badges.get_badge("github-collaborator")
if badge:
    print(f"{badge.emoji} {badge.name}: {badge.description}")
```

**`badges.get_user_badges(user)`**  
Get all badges earned by a user.

**Parameters**:
- `user`: User to get badges for

**Returns**:
- List of badges earned by the user

**Example**:
```python
from quack_core.teaching.core import badges, utils

user = utils.load_progress()
earned_badges = badges.get_user_badges(user)
print(f"You have earned {len(earned_badges)} badges:")
for badge in earned_badges:
    print(f"{badge.emoji} {badge.name}")
```

**`badges.award_badge(user, badge_id)`**  
Award a badge to a user if they don't already have it.

**Parameters**:
- `user`: User to award the badge to
- `badge_id`: ID of the badge to award

**Returns**:
- True if the badge was newly awarded, False otherwise

**Example**:
```python
from quack_core.teaching.core import badges, utils

user = utils.load_progress()
if badges.award_badge(user, "github-collaborator"):
    print("🎉 New badge awarded!")
    utils.save_progress(user)
else:
    print("Badge already earned")
```

**`badges.get_next_badges(user, limit=3)`**  
Get the next badges a user could earn.

**Parameters**:
- `user`: User to get next badges for
- `limit`: Maximum number of badges to return

**Returns**:
- List of badges the user could earn next

**Example**:
```python
from quack_core.teaching.core import badges, utils

user = utils.load_progress()
next_badges = badges.get_next_badges(user)
print("You could earn these badges next:")
for badge in next_badges:
    print(f"{badge.emoji} {badge.name}: {badge.description}")
```

**`badges.get_badge_progress(user, badge_id)`**  
Calculate a user's progress toward a specific badge.

**Parameters**:
- `user`: User to calculate progress for
- `badge_id`: ID of the badge to check

**Returns**:
- Progress as a value between 0.0 and 1.0

**Example**:
```python
from quack_core.teaching.core import badges, utils

user = utils.load_progress()
progress = badges.get_badge_progress(user, "duck-expert")
print(f"Progress toward Duck Expert badge: {progress * 100:.1f}%")
```

#### Quest Management

**`quests.get_all_quests()`**  
Get all available quests.

**Returns**:
- List of all quest definitions

**Example**:
```python
from quack_core.teaching.core import quests

all_quests = quests.get_all_quests()
print(f"Total quests available: {len(all_quests)}")
```

**`quests.get_quest(quest_id)`**  
Get a specific quest by ID.

**Parameters**:
- `quest_id`: ID of the quest to retrieve

**Returns**:
- Quest if found, None otherwise

**Example**:
```python
from quack_core.teaching.core import quests

quest = quests.get_quest("star-quack-core")
if quest:
    print(f"{quest.name}: {quest.description} (+{quest.reward_xp} XP)")
```

**`quests.get_user_quests(user)`**  
Get all quests for a user, categorized by completion status.

**Parameters**:
- `user`: User to get quests for

**Returns**:
- Dictionary with 'completed' and 'available' quests

**Example**:
```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()
user_quests = quests.get_user_quests(user)
print(f"Completed quests: {len(user_quests['completed'])}")
print(f"Available quests: {len(user_quests['available'])}")
```

**`quests.check_quest_completion(user)`**  
Check which quests a user has newly completed.

**Parameters**:
- `user`: User to check quest completion for

**Returns**:
- List of newly completed quests

**Example**:
```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()
newly_completed = quests.check_quest_completion(user)
if newly_completed:
    print(f"You've completed {len(newly_completed)} new quests!")
    for quest in newly_completed:
        print(f"- {quest.name} (+{quest.reward_xp} XP)")
```

**`quests.complete_quest(user, quest_id, forced=False)`**  
Mark a quest as completed for a user and award XP and badges.

**Parameters**:
- `user`: User to complete quest for
- `quest_id`: ID of the quest to complete
- `forced`: If True, mark as completed without verification

**Returns**:
- True if quest was newly completed, False otherwise

**Example**:
```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()
if quests.complete_quest(user, "run-tests", forced=True):
    print("Quest marked as complete!")
    utils.save_progress(user)
else:
    print("Quest already completed or not found")
```

**`quests.apply_completed_quests(user)`**  
Check for newly completed quests and update user progress.

**Parameters**:
- `user`: User to update

**Returns**:
- List of newly completed quests

**Example**:
```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()
newly_completed = quests.apply_completed_quests(user)
if newly_completed:
    print(f"You've completed {len(newly_completed)} new quests!")
    utils.save_progress(user)
```

**`quests.get_suggested_quests(user, limit=3)`**  
Get suggested quests for a user to complete next.

**Parameters**:
- `user`: User to get suggestions for
- `limit`: Maximum number of suggestions to return

**Returns**:
- List of suggested quests

**Example**:
```python
from quack_core.teaching.core import quests, utils

user = utils.load_progress()
suggested = quests.get_suggested_quests(user)
print("Suggested quests:")
for quest in suggested:
    print(f"- {quest.name}: {quest.description} (+{quest.reward_xp} XP)")
```

#### Certificate Management

**`certificates.create_certificate(user, course_id, issuer="QuackVerse", additional_data=None)`**  
Create a digital certificate for course completion.

**Parameters**:
- `user`: User to create certificate for
- `course_id`: ID of the completed course
- `issuer`: Name of the certificate issuer
- `additional_data`: Additional data to include in the certificate

**Returns**:
- Certificate data as a dictionary

**Example**:
```python
from quack_core.teaching.core import certificates, utils

user = utils.load_progress()
cert = certificates.create_certificate(
    user,
    course_id="python-basics",
    additional_data={"course_name": "Python Programming Basics"}
)
print(f"Certificate created with ID: {cert['id']}")
```

**`certificates.verify_certificate(certificate)`**  
Verify a certificate's authenticity.

**Parameters**:
- `certificate`: Certificate data to verify

**Returns**:
- True if the certificate is valid, False otherwise

**Example**:
```python
from quack_core.teaching.core import certificates

# Verify a certificate
if certificates.verify_certificate(cert):
    print("Certificate is valid and authentic")
else:
    print("Invalid certificate")
```

**`certificates.certificate_to_string(certificate)`**  
Convert a certificate to a shareable string format.

**Parameters**:
- `certificate`: Certificate data

**Returns**:
- Certificate as a base64-encoded string

**Example**:
```python
from quack_core.teaching.core import certificates

# Convert to shareable string
cert_string = certificates.certificate_to_string(cert)
print(f"Share this certificate: {cert_string}")
```

**`certificates.string_to_certificate(cert_string)`**  
Convert a certificate string back to dictionary format.

**Parameters**:
- `cert_string`: Certificate as a base64-encoded string

**Returns**:
- Certificate data as a dictionary

**Example**:
```python
from quack_core.teaching.core import certificates

# Parse a certificate from a string
try:
    parsed_cert = certificates.string_to_certificate(cert_string)
    print(f"Certificate for {parsed_cert['recipient']} - Course: {parsed_cert['course_id']}")
except ValueError:
    print("Invalid certificate string")
```

**`certificates.format_certificate_markdown(certificate)`**  
Format a certificate as a markdown string for display or sharing.

**Parameters**:
- `certificate`: Certificate data

**Returns**:
- Certificate as a formatted markdown string

**Example**:
```python
from quack_core.teaching.core import certificates

# Format for display
markdown = certificates.format_certificate_markdown(cert)
print(markdown)
```

**`certificates.has_earned_certificate(user, course_id)`**  
Check if a user has earned a certificate for a specific course.

**Parameters**:
- `user`: User to check
- `course_id`: ID of the course

**Returns**:
- True if the user has earned a certificate, False otherwise

**Example**:
```python
from quack_core.teaching.core import certificates, utils

user = utils.load_progress()
if certificates.has_earned_certificate(user, "python-basics"):
    print("You've earned the Python Basics certificate!")
else:
    print("Complete all requirements to earn this certificate")
```

#### User Progress Utilities

**`utils.load_progress()`**  
Load user progress from the progress file.

**Returns**:
- UserProgress instance

**Example**:
```python
from quack_core.teaching.core import utils

user = utils.load_progress()
print(f"Loaded user progress: Level {user.get_level()} with {user.xp} XP")
```

**`utils.save_progress(progress)`**  
Save user progress to the progress file.

**Parameters**:
- `progress`: UserProgress instance to save

**Returns**:
- True if saved successfully, False otherwise

**Example**:
```python
from quack_core.teaching.core import utils

user = utils.load_progress()
# Make changes to user progress
user.xp += 10
# Save changes
if utils.save_progress(user):
    print("Progress saved successfully")
else:
    print("Error saving progress")
```

**`utils.create_new_progress()`**  
Create new user progress.

**Returns**:
- New UserProgress instance

**Example**:
```python
from quack_core.teaching.core import utils

# Create fresh progress
new_user = utils.create_new_progress()
print(f"Created new progress with GitHub username: {new_user.github_username}")
```

**`utils.reset_progress()`**  
Reset user progress by deleting the progress file.

**Returns**:
- True if reset successfully, False otherwise

**Example**:
```python
from quack_core.teaching.core import utils

if utils.reset_progress():
    print("Progress reset successfully")
else:
    print("Error resetting progress")
```

**`utils.backup_progress(backup_name=None)`**  
Create a backup of the user progress file.

**Parameters**:
- `backup_name`: Optional name for the backup file

**Returns**:
- True if backed up successfully, False otherwise

**Example**:
```python
from quack_core.teaching.core import utils

# Create a backup
if utils.backup_progress("before_changes"):
    print("Backup created successfully")
else:
    print("Error creating backup")
```

This completes the detailed documentation for the QuackCore Teaching Module. With this guide, junior developers should be able to understand and leverage the module's capabilities to create engaging educational experiences with gamification.