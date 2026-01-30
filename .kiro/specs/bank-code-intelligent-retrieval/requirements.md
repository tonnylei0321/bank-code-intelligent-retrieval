# 需求文档

## 介绍

联行号智能检索系统是一个企业级的小模型训练和部署平台，支持基于大模型的智能训练和微调功能。该系统使组织能够构建、训练和部署专门的AI模型，用于高精度、高性能的银行联行号检索。第一阶段实现智能银行联行号检索小模型，能够理解自然语言查询并返回准确的银行代码和信息。

## 术语表

- **System**: 联行号智能检索系统
- **Small_Model**: 用于银行联行号检索的微调专用模型（基于Qwen2.5-0.5B/1.5B）
- **Large_Model**: 用于训练数据生成的教师模型（阿里通义千问API）
- **Training_Engine**: 负责模型训练和微调的后端服务
- **Query_Service**: 使用训练好的模型处理用户查询的推理服务
- **RAG_System**: 检索增强生成系统，用于提高查询准确性
- **Bank_Code**: 中国银行系统使用的12位银行识别代码
- **LoRA**: 低秩适应技术，用于高效模型微调
- **Smart_Generator**: 从标准银行数据生成多样化训练样本的服务
- **Frontend_System**: 基于React的系统管理Web界面
- **Backend_System**: 基于FastAPI的服务器，处理训练、推理和数据管理

## Requirements

### Requirement 1: User Authentication and Authorization

**User Story:** As a system administrator, I want secure user authentication and role-based access control, so that I can manage system access and protect sensitive banking data.

#### Acceptance Criteria

1. WHEN a user attempts to access the system, THE System SHALL require valid authentication credentials
2. WHEN a user logs in with valid credentials, THE System SHALL create a secure session with appropriate permissions
3. WHEN a user attempts to access admin functions, THE System SHALL verify admin role permissions
4. WHEN a user session expires, THE System SHALL require re-authentication
5. THE System SHALL support role-based access control with user and admin roles

### Requirement 2: Training Data Management

**User Story:** As a data manager, I want to upload, validate, and manage training datasets, so that I can prepare high-quality data for model training.

#### Acceptance Criteria

1. WHEN a user uploads a dataset file, THE System SHALL validate the file format and structure
2. WHEN a dataset is uploaded, THE System SHALL extract and count total records
3. WHEN dataset validation is requested, THE System SHALL identify valid and invalid records
4. WHEN a dataset contains bank information, THE System SHALL extract bank names and codes
5. THE System SHALL support CSV, Excel, and .unl file formats
6. WHEN dataset statistics are requested, THE System SHALL provide record counts and quality metrics

### Requirement 3: Intelligent Training Data Generation

**User Story:** As a training manager, I want to automatically generate diverse training samples from standard bank data, so that I can improve model accuracy and handle various user query patterns.

#### Acceptance Criteria

1. WHEN smart generation is enabled, THE Smart_Generator SHALL create multiple natural language variations for each bank
2. WHEN generating samples, THE Smart_Generator SHALL produce complete names, abbreviations, colloquial expressions, and location-based queries
3. WHEN using rule-based generation, THE Smart_Generator SHALL generate 5-10 diverse question patterns per bank
4. WHEN using LLM enhancement, THE Smart_Generator SHALL leverage large models for more natural question generation
5. THE Smart_Generator SHALL support configurable sample counts per bank (3-15 samples)
6. WHEN generation is complete, THE System SHALL provide statistics on generated samples and banks processed

### Requirement 4: Model Training and Fine-tuning

**User Story:** As a model trainer, I want to train specialized small models using prepared datasets, so that I can create accurate bank code retrieval models.

#### Acceptance Criteria

1. WHEN a training job is created, THE Training_Engine SHALL validate dataset availability and parameters
2. WHEN training starts, THE Training_Engine SHALL load the base model and apply LoRA fine-tuning
3. WHEN training is in progress, THE Training_Engine SHALL provide real-time progress updates and loss metrics
4. WHEN training completes successfully, THE Training_Engine SHALL save the trained model weights
5. THE Training_Engine SHALL support multiple base models (Qwen2.5-0.5B, Qwen2.5-1.5B, Qwen2.5-3B)
6. WHEN training fails, THE Training_Engine SHALL log error details and allow restart
7. THE Training_Engine SHALL support configurable training parameters (learning rate, epochs, batch size, LoRA parameters)

### Requirement 5: RAG-Enhanced Query Processing

**User Story:** As an end user, I want to query bank information using natural language, so that I can quickly find accurate bank codes and details.

#### Acceptance Criteria

1. WHEN a user submits a query, THE RAG_System SHALL extract relevant entities from the question
2. WHEN entities are extracted, THE RAG_System SHALL retrieve relevant bank records from the database
3. WHEN relevant records are found, THE Query_Service SHALL use the small model to generate accurate answers
4. WHEN multiple matches exist, THE Query_Service SHALL select the best match using intelligent scoring
5. THE Query_Service SHALL return bank names and 12-digit bank codes in structured format
6. WHEN no matches are found, THE Query_Service SHALL provide helpful error messages

### Requirement 6: Performance and Accuracy Requirements

**User Story:** As a system operator, I want the system to meet strict performance and accuracy standards, so that it can handle production workloads reliably.

#### Acceptance Criteria

1. WHEN processing queries, THE Query_Service SHALL achieve ≥99.9% accuracy for bank code retrieval
2. WHEN a query is submitted, THE Query_Service SHALL respond within milliseconds
3. WHEN multiple concurrent users access the system, THE System SHALL maintain performance under high load
4. WHEN caching is enabled, THE Query_Service SHALL improve response times for repeated queries
5. THE System SHALL support both GPU (CUDA/MPS) and CPU inference modes

### Requirement 7: Query History and Logging

**User Story:** As a system administrator, I want comprehensive query logging and history tracking, so that I can monitor system usage and performance.

#### Acceptance Criteria

1. WHEN a query is processed, THE System SHALL log the question, answer, confidence score, and response time
2. WHEN query history is requested, THE System SHALL provide paginated results with filtering options
3. WHEN logging is enabled, THE System SHALL record user ID, timestamp, and model version
4. THE System SHALL provide query statistics and performance metrics
5. WHEN cache statistics are requested, THE System SHALL report hit rates and cache performance

### Requirement 8: System Extensibility and Architecture

**User Story:** As a system architect, I want clear separation between components and extensible architecture, so that the system can support future business models and requirements.

#### Acceptance Criteria

1. WHEN new business models are needed, THE System SHALL support training additional specialized models
2. WHEN transport mechanisms are changed, THE message handling and UI components SHALL remain unaffected
3. WHEN UI implementations are modified, THE transport and query logic SHALL continue functioning unchanged
4. THE System SHALL maintain clear separation between frontend, backend, training, and inference components
5. THE System SHALL support private deployment with configurable database connections

### Requirement 9: Frontend Management Interface

**User Story:** As a system user, I want an intuitive web interface to manage data, training, and queries, so that I can efficiently operate the system without technical expertise.

#### Acceptance Criteria

1. WHEN accessing the data management page, THE Frontend_System SHALL display dataset lists with upload capabilities
2. WHEN viewing training management, THE Frontend_System SHALL show job status, progress, and controls
3. WHEN using the query interface, THE Frontend_System SHALL provide real-time question answering with history
4. WHEN monitoring system status, THE Frontend_System SHALL display performance metrics and health indicators
5. THE Frontend_System SHALL support responsive design for various screen sizes
6. WHEN errors occur, THE Frontend_System SHALL display user-friendly error messages

### Requirement 10: Data Serialization and Storage

**User Story:** As a system developer, I want reliable data persistence and serialization, so that training data, models, and query logs are safely stored and retrievable.

#### Acceptance Criteria

1. WHEN storing training datasets, THE System SHALL serialize data using JSON format
2. WHEN saving model weights, THE System SHALL use standard PyTorch/HuggingFace formats
3. WHEN persisting query logs, THE System SHALL store structured data in the relational database
4. WHEN backing up data, THE System SHALL maintain data integrity and consistency
5. THE System SHALL support database migrations and schema updates

### Requirement 11: Error Handling and Recovery

**User Story:** As a system operator, I want robust error handling and recovery mechanisms, so that the system remains stable and provides helpful feedback during failures.

#### Acceptance Criteria

1. WHEN model loading fails, THE Query_Service SHALL provide clear error messages and fallback options
2. WHEN training encounters errors, THE Training_Engine SHALL log detailed error information and allow restart
3. WHEN database connections fail, THE System SHALL attempt reconnection and graceful degradation
4. WHEN memory issues occur, THE System SHALL implement proper cleanup and resource management
5. WHEN API calls fail, THE System SHALL provide retry mechanisms with exponential backoff

### Requirement 12: Configuration and Deployment

**User Story:** As a deployment engineer, I want flexible configuration options and deployment support, so that I can deploy the system in various environments.

#### Acceptance Criteria

1. WHEN deploying the system, THE System SHALL support environment-specific configuration files
2. WHEN configuring models, THE System SHALL allow selection of different base models and parameters
3. WHEN setting up databases, THE System SHALL support multiple database backends
4. THE System SHALL support Docker containerization for consistent deployment
5. WHEN scaling the system, THE System SHALL support horizontal scaling of inference services