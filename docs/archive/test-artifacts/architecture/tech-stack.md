# Technology Stack - Approved Technologies

> **TEST ARTIFACT ONLY:** This document is a test fixture for validating the `architecture-compliance-checker` sub-agent. It represents a fictional web application project, not PRISM itself. PRISM is a Claude Code plugin with no technology stack - it operates using Claude Code's architecture (skills, agents, hooks, workflows).

## Backend
- **Runtime**: Node.js 18+ LTS
- **Framework**: Express 4.x
- **Language**: TypeScript 5.x
- **Database**: PostgreSQL 14+
- **ORM**: Prisma 5.x
- **Authentication**: JWT (jsonwebtoken library)
- **Testing**: Jest, Supertest
- **Validation**: Zod

## Frontend
- **Framework**: React 18+
- **Language**: TypeScript 5.x
- **State Management**: Zustand or React Context
- **Routing**: React Router 6.x
- **UI Components**: Tailwind CSS, Radix UI
- **Forms**: React Hook Form + Zod
- **Testing**: Jest, React Testing Library, Playwright

## Infrastructure
- **Cloud**: AWS or Azure
- **Storage**: AWS S3 or Azure Blob Storage
- **CDN**: CloudFront or Azure CDN
- **Caching**: Redis
- **Container**: Docker
- **Orchestration**: Kubernetes (production)

## Development Tools
- **Version Control**: Git
- **Package Manager**: npm or pnpm
- **Code Quality**: ESLint, Prettier
- **Pre-commit**: Husky
- **CI/CD**: GitHub Actions or Azure DevOps

## Deprecated / Not Approved
- ❌ Vue.js (use React)
- ❌ MongoDB (use PostgreSQL)
- ❌ Redux (use Zustand or Context)
- ❌ JavaScript without TypeScript
- ❌ Class components (use functional components)
