# WikiEval Project Description

WikiEval Platform

WikiEval is a web platform for organizing and managing Wikipedia editing contests (edit-a-thons), enabling users to create contests, submit article edits, track submissions, and compete in leaderboards with proper authentication and role-based access control.

## Overview

The platform facilitates collaborative Wikipedia editing competitions by providing contest management tools, submission tracking, automated template enforcement, and jury review workflows. It integrates with Wikimedia OAuth for secure authentication and supports deployment on Wikimedia Toolforge.

## Key Features

- **Contest Management**: Create and manage editing contests with configurable parameters (dates, categories, byte count ranges, template requirements)
- **Article Submission**: Submit Wikipedia articles to contests with automatic template attachment and validation
- **Jury Review System**: Review and score submissions with acceptance/rejection workflows
- **Leaderboards**: Real-time ranking of participants based on submission quality and quantity
- **User Authentication**: Secure login via email/password or Wikimedia OAuth 1.0a
- **Role-Based Access**: Differentiated permissions for users, contest creators, jury members, and administrators
- **Template Enforcement**: Automatic validation and attachment of contest templates to submitted articles

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy ORM, Alembic for database migrations
- **Frontend**: Vue.js 3 with Vite, Vue Router, and Bootstrap 5
- **Database**: MySQL (production) or SQLite (development)
- **Authentication**: JWT tokens in HTTP-only cookies with CSRF protection, plus Wikimedia OAuth 1.0a
- **Deployment**: Local development environment and Wikimedia Toolforge production deployment

## Project Links

- **Repository**: [Link to repository if available]
- **Documentation**: See `docs/PROJECT_DOCUMENTATION.md` for detailed architecture and API documentation
- **Development Guide**: See `docs/DEVELOPMENT_GUIDE.md` for setup and development instructions
- **Toolforge Deployment**: See `docs/TOOLFORGE_DEPLOYMENT.md` for production deployment guide

## Use Cases

- Organizing Wikipedia edit-a-thons with structured submission and review processes
- Running article improvement contests with automated template management
- Tracking and scoring collaborative editing efforts across multiple participants
- Managing jury workflows for evaluating contest submissions

## Related Projects

This project integrates with Wikimedia infrastructure and follows Wikimedia development practices for OAuth authentication and Toolforge deployment.

