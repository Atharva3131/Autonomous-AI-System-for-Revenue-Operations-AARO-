# Autonomous AI Agent for Revenue Operations (AARO)

A production-ready AI system designed specifically for B2B SaaS and service companies to optimize revenue operations. The AARO continuously monitors sales pipeline data, detects revenue leakage and execution gaps, enforces sales SOPs using internal knowledge, and executes corrective actions automatically with appropriate human oversight.

## Features

- **Automated CRM Data Ingestion**: Connects to CRM systems for deals, pipeline, and sales activity data
- **Intelligent Pipeline Risk Detection**: Identifies stalled deals, missed follow-ups, and SOP deviations
- **Context-Aware Sales Decision Making**: Uses RAG-based knowledge management for sales playbooks and SOPs
- **Automated Sales Action Execution**: Executes approved decisions through follow-up tasks, deal updates, and manager alerts
- **Sales Management Oversight**: Manages approval workflows for high-impact revenue decisions
- **Comprehensive Revenue Observability**: Tracks pipeline recovery, velocity improvements, and manual work reduction

## Revenue Intelligence Rules

The AARO automatically detects:
- Deals stalled in a stage beyond defined thresholds
- Meetings completed without a next action
- High-value opportunities with no recent activity
- Leads contacted fewer than N times
- Reps deviating from defined sales SOPs

## Revenue-Focused Actions

The AARO can automatically:
- Create and assign follow-up tasks
- Generate context-aware follow-up messages
- Update deal stages or flags
- Alert sales managers about pipeline risks
- Produce weekly pipeline risk and recovery reports

## Success Metrics (RevOps Only)

Track and surface:
- % of stalled pipeline recovered
- Average deal velocity improvement
- Reduction in manual RevOps work
- Number of autonomous interventions executed

## Architecture

The AARO follows a modular, layered architecture optimized for revenue operations:

- **Sales Data Ingestion Layer**: Collects and normalizes CRM data, deals, pipeline, and sales activities
- **Sales Knowledge Management Layer**: RAG-based system for sales SOPs, playbooks, and successful deal patterns
- **Revenue Intelligence Layer**: Pipeline risk detection and sales decision classification
- **Sales Action Execution Layer**: Automated sales action execution with retry logic
- **Sales Management Loop**: Approval workflows for high-impact revenue decisions
- **Revenue Observability System**: Comprehensive logging and revenue impact metrics

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aboa
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment configuration:
```bash
cp .env.example .env
```

5. Update the `.env` file with your configuration values.

### Running the Application

Start the development server:
```bash
python -m aboa.main
```

Or using uvicorn directly:
```bash
uvicorn aboa.main:app --reload
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## Configuration

The application uses environment variables for configuration. See `.env.example` for all available options.

Key configuration areas:
- Application settings (host, port, debug mode)
- Security settings (secret key, CORS origins)
- Logging configuration (level, format, file output)
- CRM integrations (database, vector DB, workflow automation)
- Revenue operations rules (follow-up days, stall thresholds, high-value deal limits)
- Retry and timeout settings

## License

This project is licensed under the MIT License - see the LICENSE file for details.