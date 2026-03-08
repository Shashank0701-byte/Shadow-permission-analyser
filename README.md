Shadow Permission Analyzer

Graph-Based AWS IAM Privilege Escalation Detection

Shadow Permission Analyzer is a cloud security tool that detects hidden privilege escalation paths in AWS IAM environments by modeling identity relationships as a graph and performing traversal analysis.

Modern cloud infrastructures contain thousands of IAM roles, policies, and trust relationships. These complex identity relationships often create unintended privilege escalation paths that are extremely difficult for security teams to detect manually.

This project automatically discovers those hidden paths and highlights high-risk identities that could potentially reach sensitive permissions such as AdministratorAccess.

Problem

Cloud breaches increasingly occur due to identity misconfigurations rather than software vulnerabilities.

In large AWS environments:

Thousands of IAM roles exist

Hundreds of policies interact

Trust relationships create hidden privilege paths

Security teams cannot manually audit these relationships.

For example:

User → Role → Role → Policy → Resource

Even if a user does not have direct admin access, they may still reach administrator privileges through chained role assumptions or policy attachments.

This phenomenon is known as shadow permissions.

Solution

Shadow Permission Analyzer converts IAM configurations into a graph model and automatically detects privilege escalation paths.

Workflow:

AWS IAM Data
        ↓
boto3 extraction
        ↓
Graph modeling (Neo4j)
        ↓
Graph traversal (BFS/DFS)
        ↓
Escalation path detection
        ↓
Risk scoring and visualization

The system highlights:

escalation chains

high-risk users

critical bridge roles

sensitive resource access

Key Features
IAM Graph Modeling

Transforms IAM relationships into a graph structure.

Nodes:

Users

Roles

Policies

Resources

Edges:

AssumeRole

AttachPolicy

PassRole

ResourceAccess

Privilege Escalation Detection

Detects chains such as:

Intern_A
   ↓
DevRole
   ↓
AdminRole
   ↓
AdministratorAccess

These chains represent potential privilege escalation attacks.

Risk Scoring

Each identity receives a risk score based on:

privilege level of the target resource

number of escalation paths

depth of escalation chain

Example scoring model:

Risk Score =
(Target Privilege Weight × 10)
+ (Escalation Path Count × 5)
+ (Path Depth × 3)
Graph Visualization

Interactive dashboard visualizes IAM relationships and escalation paths.

Security teams can immediately identify:

high-risk identities

critical roles

attack chains

System Architecture
AWS IAM
   │
   │  (boto3 SDK)
   ▼
Data Extraction Layer
   │
   ▼
Graph Database (Neo4j)
   │
   ▼
Privilege Escalation Engine
   │
   ▼
React Security Dashboard
Technology Stack

Backend

Python

boto3

Neo4j

FastAPI

Frontend

React

Graph visualization libraries

Security Concepts

AWS IAM

Privilege escalation analysis

Graph traversal algorithms

Example Escalation Chain

Detected attack path:

Intern_A
   ↓
InternRole
   ↓
DevRole
   ↓
AdminRole
   ↓
AdministratorAccess

This means a low-privilege user could potentially escalate privileges through chained role assumptions.

Why Graph Analysis?

IAM policies are stored as complex JSON structures, making manual analysis extremely difficult.

By converting permissions into graph relationships, privilege escalation becomes a path detection problem, which can be solved efficiently using graph traversal algorithms.

Real-World Motivation

Identity misconfigurations have led to several major breaches, including the 2019 Capital One breach, where attackers accessed sensitive data through an overly permissive IAM role.

Industry research predicts that the majority of cloud security failures occur due to misconfigured identity permissions.

Future Work

Potential improvements include:

Real-time IAM monitoring using CloudTrail events

Multi-cloud support (AWS, Azure, GCP)

AI-assisted risk explanation

Automated remediation recommendations

Repository Structure
shadow-permission-analyzer
│
├── backend
│   ├── IAM data extraction
│   ├── graph modeling
│   └── escalation detection
│
├── frontend
│   ├── dashboard
│   └── graph visualization
│
├── dataset
│   └── sample IAM data
Installation

Clone the repository:

git clone https://github.com/yourusername/shadow-permission-analyzer.git

Install dependencies:

pip install -r requirements.txt

Run backend:

python app.py

Run frontend:

npm install
npm start

Authors
Shashank Chakraborty and Pratyush Kumar

Developed as part of a cybersecurity project exploring graph-based privilege escalation detection in cloud identity systems.
