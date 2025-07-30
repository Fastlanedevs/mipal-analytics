# Analytics Module

The Analytics Module provides a comprehensive data analytics platform that allows users to connect to various data sources, visualize data through charts, and organize these visualizations in dashboards.

## Architecture Overview

The analytics module follows a layered architecture pattern:

```
┌────────────┐      ┌────────────┐      ┌────────────┐      ┌────────────┐
│    API     │──────│  Service   │──────│ Repository │──────│  Storage   │
│   Layer    │      │   Layer    │      │   Layer    │      │   Layer    │
└────────────┘      └────────────┘      └────────────┘      └────────────┘
```

## Core Components

### Data Model (Entity Layer)

The core entities of the analytics module are:

- **Database**: Represents a data source (PostgreSQL database or CSV files)

  - Supports various database types (PostgreSQL, CSV)
  - Contains tables and credentials
  - Has lifecycle management (create, delete, restore)

- **Table**: Represents a table within a database

  - Contains columns, statistics, and metadata
  - Supports soft deletion and restoration
  - Has storage information (S3 path, etc.)

- **Column**: Represents a column within a table

  - Contains data type, constraints, and statistics

- **Chart**: Represents a visualization of data

  - Various types of visualizations
  - Contains configuration, dimensions, and data

- **Dashboard**: Collection of charts
  - Layout configuration for charts
  - Sharing and access control

### Service Layer

The service layer contains the business logic and coordinates operations between components:

- **AnalyticsService**: Main coordinating service for analytics operations

  - Database and table management
  - Schema mapping and recommendations

- **PostgresService**: Handles PostgreSQL-specific operations

  - Connection management
  - Query execution

- **ChartService**: Manages chart creation and manipulation

  - Chart generation and configuration
  - Chart rendering and export

- **DashboardService**: Handles dashboard operations

  - Dashboard creation and layout
  - Chart management within dashboards

- **SchemaService**: Handles database schema operations
  - Schema discovery and mapping
  - Data profiling

### Repository Layer

The repository layer handles data access and persistence:

- **AnalyticsRepository**: Handles storage and retrieval of analytics entities

  - CRUD operations for databases, tables, columns
  - Data querying and transformation

- **ChartRepository**: Manages chart data storage and retrieval
  - Chart metadata and configuration storage
  - Chart version history

### API Layer

The API layer exposes the functionality through RESTful endpoints:

- **Database Management**: CRUD operations for databases
- **Table Management**: Operations for tables within databases
- **Chart Management**: Creation, visualization, and modification of charts
- **Dashboard Management**: Creation and management of dashboards
- **Schema Management**: Database schema discovery and mapping

## Data Flow

### Database Connection Flow

```
┌────────┐   1. Connect    ┌────────────┐    2. Validate    ┌─────────────┐
│  User  │─────────────────▶ API Layer  │──────────────────▶│ Postgres    │
└────────┘                 └────────────┘                   │ Service     │
                                │                           └─────────────┘
                                │                                  │
                                │                                  │
┌────────────────┐   4. Store   │                                  │
│  Analytics     │◀─────────────┘                                  │
│  Repository    │                                                 │
└────────────────┘                  3. Map Schema                  │
        │                  ┌─────────────────────────────────────┐ │
        │                  │                                     │ │
        └─────────────────▶│           Schema Service           │◀┘
                           └─────────────────────────────────────┘
```

### Chart Creation Flow

```
┌────────┐   1. Request   ┌────────────┐    2. Process    ┌─────────────┐
│  User  │─────────────────▶ API Layer  │──────────────────▶│ Chart       │
└────────┘                 └────────────┘                   │ Service     │
                                                           └─────────────┘
                                                                  │
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │  Analytics  │
                                                           │  Repository │
                                                           └─────────────┘
                                                                  │
                                                                  │
                                                                  ▼
                                                           ┌─────────────┐
                                                           │  Render &   │
                                                           │  Response   │
                                                           └─────────────┘
```

#### Detailed Chart Creation Process

The chart creation process involves several layers and leverages AI to automatically generate appropriate visualizations:

1. **API Request Handling**

   - Route: `POST /charts` accepts a `CreateChartRequestDTO` containing:
     - `message_id`: ID of the message containing data to visualize
     - `visibility`: Chart visibility setting (PRIVATE/SHARED/PUBLIC)
   - Controller performs validation and passes request to Chart Service

2. **Chart Service Processing**

   - `ChartService.create_chart` method:
     - Retrieves message data using `MessageNode`
     - Extracts data rows, column metadata, and query information
     - Validates data availability and structure

3. **Chart Generation Service**

   - `chart_generation_service.generate_chart_schema` method:
     - Receives sample data (limited to 100 rows)
     - Processes column metadata
     - Prepares input for AI-based chart generation

4. **Chart Generation Agent (LLM-based)**

   - `ChartGenerationAgent` initialized with:
     - GPT model (GPT-4o, GPT-4o-mini, etc.)
     - Specialized prompts for chart generation
   - The agent analyzes data characteristics to determine:
     - Most appropriate chart type
     - Optimal field mappings
     - Chart configuration in Vega-Lite format
     - Alternative visualization options

5. **Schema Processing**

   - Chart schema validated and enhanced:
     - Special processing for specific chart types (pie, grouped bar, etc.)
     - Field mappings calculated for future adjustments
     - Metadata organized (config, data references, encodings)

6. **Repository Storage**

   - `chart_repository.create_chart` method:
     - Stores chart data and schema
     - Links to originating message
     - Saves ownership information
     - Stores available adjustments and alternatives

7. **API Response**
   - Chart entity converted to `ChartResponseDTO`
   - Response returned with status code 201

```
┌────────────┐     ┌────────────┐     ┌────────────────────┐
│            │     │            │     │                    │
│ API Route  │────▶│  Chart     │────▶│ Chart Generation   │
│ POST       │     │  Service   │     │ Service            │
│ /charts    │     │            │     │                    │
└────────────┘     └────────────┘     └────────────────────┘
                                                │
                                                ▼
┌────────────┐     ┌────────────┐     ┌────────────────────┐
│            │     │            │     │                    │
│ API        │◀────│ Chart      │◀────│ Chart Generation   │
│ Response   │     │ Repository │     │ Agent (LLM)        │
│            │     │            │     │                    │
└────────────┘     └────────────┘     └────────────────────┘
```

This AI-driven approach automatically selects the most appropriate visualization for the data without requiring manual configuration, making it easy for users to create insightful charts.

## Key Features

1. **Multi-source Data Connection**: Connect to PostgreSQL databases or upload CSV files
2. **Schema Discovery**: Automatically map and profile database schemas
3. **Data Visualization**: Create charts and visualizations from data sources
4. **Dashboard Creation**: Organize charts into interactive dashboards
5. **Soft Delete/Restore**: Support for soft deletion and restoration of resources
6. **Recommendations**: Get intelligent recommendations for visualizations

## Error Handling

The module uses a dedicated error system with specific error types:

- DatabaseNotFoundError
- TableNotFoundError
- ChartNotFoundError
- DashboardNotFoundError
- And others for specific scenarios

## API Endpoints

The module exposes a comprehensive REST API for all operations:

- `GET /databases`: List all databases
- `POST /postgres/databases`: Create a PostgreSQL database connection
- `POST /csv/databases`: Upload CSV files as a database
- `POST /charts`: Create a new chart
- `GET /charts/{chart_id}`: Get chart details
- `POST /dashboards`: Create a dashboard
- And many more for complete functionality
