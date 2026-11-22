-- CampusCare AI database schema (Azure SQL Database / T-SQL).
-- Safe to run more than once: every object is created only if it does not exist yet.
-- Run it with:  python backend/scripts/init_db.py
-- "GO" lines separate batches; the init script understands them.
SET NOCOUNT ON;
GO

-- ---------------------------------------------------------------- Departments
IF OBJECT_ID(N'dbo.Departments', N'U') IS NULL
CREATE TABLE dbo.Departments (
    DepartmentId INT IDENTITY(1,1) CONSTRAINT PK_Departments PRIMARY KEY,
    Name         NVARCHAR(100) NOT NULL CONSTRAINT UQ_Departments_Name UNIQUE,
    CreatedAt    DATETIME2(0)  NOT NULL CONSTRAINT DF_Departments_CreatedAt DEFAULT SYSUTCDATETIME()
);
GO

-- ---------------------------------------------------------------------- Users
-- Role is set by the server. Students register themselves; staff and admins are created by an administrator.
IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
CREATE TABLE dbo.Users (
    UserId           INT IDENTITY(1,1) CONSTRAINT PK_Users PRIMARY KEY,
    FullName         NVARCHAR(100) NOT NULL,
    Email            NVARCHAR(254) NOT NULL CONSTRAINT UQ_Users_Email UNIQUE,
    PasswordHash     NVARCHAR(255) NOT NULL,
    Role             VARCHAR(10)   NOT NULL CONSTRAINT CK_Users_Role CHECK (Role IN ('student', 'staff', 'admin')),
    DepartmentId     INT NULL CONSTRAINT FK_Users_Departments REFERENCES dbo.Departments (DepartmentId),
    EnrollmentId     NVARCHAR(40)  NULL,
    IsActive         BIT           NOT NULL CONSTRAINT DF_Users_IsActive DEFAULT 1,
    FailedLoginCount INT           NOT NULL CONSTRAINT DF_Users_FailedLoginCount DEFAULT 0,
    LockoutUntil     DATETIME2(0)  NULL,
    CreatedAt        DATETIME2(0)  NOT NULL CONSTRAINT DF_Users_CreatedAt DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_Users_StaffHasDepartment CHECK (Role <> 'staff' OR DepartmentId IS NOT NULL)
);
GO

-- ----------------------------------------------------------------- Categories
-- Managed by admins. Keywords (comma separated, lowercase) feed the rule-based classifier.
IF OBJECT_ID(N'dbo.Categories', N'U') IS NULL
CREATE TABLE dbo.Categories (
    CategoryId      INT IDENTITY(1,1) CONSTRAINT PK_Categories PRIMARY KEY,
    Name            NVARCHAR(100) NOT NULL CONSTRAINT UQ_Categories_Name UNIQUE,
    DepartmentId    INT NOT NULL CONSTRAINT FK_Categories_Departments REFERENCES dbo.Departments (DepartmentId),
    DefaultPriority VARCHAR(10)   NOT NULL CONSTRAINT CK_Categories_Priority CHECK (DefaultPriority IN ('Low', 'Medium', 'High', 'Critical')),
    Keywords        NVARCHAR(1000) NOT NULL CONSTRAINT DF_Categories_Keywords DEFAULT '',
    CreatedAt       DATETIME2(0)  NOT NULL CONSTRAINT DF_Categories_CreatedAt DEFAULT SYSUTCDATETIME()
);
GO

-- ---------------------------------------------------------------- Complaints
-- Reference is the public ID shown to people (CC-2026-0001). ComplaintId is the internal key.
IF NOT EXISTS (SELECT 1 FROM sys.sequences WHERE name = N'ComplaintNumberSeq')
CREATE SEQUENCE dbo.ComplaintNumberSeq AS INT START WITH 1 INCREMENT BY 1;
GO

IF OBJECT_ID(N'dbo.Complaints', N'U') IS NULL
CREATE TABLE dbo.Complaints (
    ComplaintId    INT IDENTITY(1,1) CONSTRAINT PK_Complaints PRIMARY KEY,
    Reference      VARCHAR(20)    NOT NULL CONSTRAINT UQ_Complaints_Reference UNIQUE,
    Title          NVARCHAR(100)  NOT NULL,
    Description    NVARCHAR(1000) NOT NULL,
    CategoryId     INT NOT NULL CONSTRAINT FK_Complaints_Categories REFERENCES dbo.Categories (CategoryId),
    Location       NVARCHAR(100)  NOT NULL,
    Priority       VARCHAR(10)    NOT NULL CONSTRAINT CK_Complaints_Priority CHECK (Priority IN ('Low', 'Medium', 'High', 'Critical')),
    Status         VARCHAR(12)    NOT NULL CONSTRAINT DF_Complaints_Status DEFAULT 'Submitted'
                   CONSTRAINT CK_Complaints_Status CHECK (Status IN ('Submitted', 'Assigned', 'In Progress', 'Resolved')),
    StudentId      INT NOT NULL CONSTRAINT FK_Complaints_Students REFERENCES dbo.Users (UserId),
    DueAt          DATETIME2(0)   NOT NULL,
    ResolvedAt     DATETIME2(0)   NULL,
    ResolutionNote NVARCHAR(500)  NULL,
    IsEscalated    BIT            NOT NULL CONSTRAINT DF_Complaints_IsEscalated DEFAULT 0,
    EscalatedAt    DATETIME2(0)   NULL,
    -- What the classifier suggested at submission time (rules or Foundry).
    AiCategoryId   INT NULL CONSTRAINT FK_Complaints_AiCategory REFERENCES dbo.Categories (CategoryId),
    AiDepartmentId INT NULL CONSTRAINT FK_Complaints_AiDepartment REFERENCES dbo.Departments (DepartmentId),
    AiPriority     VARCHAR(10)    NULL CONSTRAINT CK_Complaints_AiPriority CHECK (AiPriority IN ('Low', 'Medium', 'High', 'Critical')),
    AiExplanation  NVARCHAR(500)  NULL,
    AiSource       VARCHAR(10)    NULL CONSTRAINT CK_Complaints_AiSource CHECK (AiSource IN ('rules', 'foundry')),
    CreatedAt      DATETIME2(0)   NOT NULL CONSTRAINT DF_Complaints_CreatedAt DEFAULT SYSUTCDATETIME(),
    UpdatedAt      DATETIME2(0)   NOT NULL CONSTRAINT DF_Complaints_UpdatedAt DEFAULT SYSUTCDATETIME()
);
GO

-- ---------------------------------------------------------------- Assignments
-- Full assignment history. Exactly one row per complaint has IsCurrent = 1.
IF OBJECT_ID(N'dbo.Assignments', N'U') IS NULL
CREATE TABLE dbo.Assignments (
    AssignmentId INT IDENTITY(1,1) CONSTRAINT PK_Assignments PRIMARY KEY,
    ComplaintId  INT NOT NULL CONSTRAINT FK_Assignments_Complaints REFERENCES dbo.Complaints (ComplaintId),
    DepartmentId INT NOT NULL CONSTRAINT FK_Assignments_Departments REFERENCES dbo.Departments (DepartmentId),
    StaffId      INT NOT NULL CONSTRAINT FK_Assignments_Staff REFERENCES dbo.Users (UserId),
    AssignedBy   INT NOT NULL CONSTRAINT FK_Assignments_AssignedBy REFERENCES dbo.Users (UserId),
    AssignedAt   DATETIME2(0) NOT NULL CONSTRAINT DF_Assignments_AssignedAt DEFAULT SYSUTCDATETIME(),
    IsCurrent    BIT NOT NULL CONSTRAINT DF_Assignments_IsCurrent DEFAULT 1
);
GO

-- --------------------------------------------------------------- StatusHistory
-- ChangedBy is NULL when the system itself made the change (for example an escalation).
IF OBJECT_ID(N'dbo.StatusHistory', N'U') IS NULL
CREATE TABLE dbo.StatusHistory (
    HistoryId   INT IDENTITY(1,1) CONSTRAINT PK_StatusHistory PRIMARY KEY,
    ComplaintId INT NOT NULL CONSTRAINT FK_StatusHistory_Complaints REFERENCES dbo.Complaints (ComplaintId),
    Status      VARCHAR(12) NOT NULL CONSTRAINT CK_StatusHistory_Status CHECK (Status IN ('Submitted', 'Assigned', 'In Progress', 'Resolved')),
    Note        NVARCHAR(500) NULL,
    ChangedBy   INT NULL CONSTRAINT FK_StatusHistory_Users REFERENCES dbo.Users (UserId),
    ChangedAt   DATETIME2(0) NOT NULL CONSTRAINT DF_StatusHistory_ChangedAt DEFAULT SYSUTCDATETIME()
);
GO

-- ------------------------------------------------------------------- Feedback
IF OBJECT_ID(N'dbo.Feedback', N'U') IS NULL
CREATE TABLE dbo.Feedback (
    FeedbackId  INT IDENTITY(1,1) CONSTRAINT PK_Feedback PRIMARY KEY,
    ComplaintId INT NOT NULL,
    StudentId   INT NOT NULL CONSTRAINT FK_Feedback_Students REFERENCES dbo.Users (UserId),
    Rating      TINYINT NOT NULL CONSTRAINT CK_Feedback_Rating CHECK (Rating BETWEEN 1 AND 5),
    Comment     NVARCHAR(500) NULL,
    CreatedAt   DATETIME2(0) NOT NULL CONSTRAINT DF_Feedback_CreatedAt DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Feedback_Complaint UNIQUE (ComplaintId),   -- one rating per complaint
    CONSTRAINT FK_Feedback_Complaints FOREIGN KEY (ComplaintId) REFERENCES dbo.Complaints (ComplaintId)
);
GO

-- ---------------------------------------------------------------- Attachments
-- Only the blob NAME is stored here. The file itself lives in Azure Blob Storage.
IF OBJECT_ID(N'dbo.Attachments', N'U') IS NULL
CREATE TABLE dbo.Attachments (
    AttachmentId INT IDENTITY(1,1) CONSTRAINT PK_Attachments PRIMARY KEY,
    ComplaintId  INT NOT NULL CONSTRAINT FK_Attachments_Complaints REFERENCES dbo.Complaints (ComplaintId),
    BlobName     NVARCHAR(200) NOT NULL CONSTRAINT UQ_Attachments_BlobName UNIQUE,
    OriginalName NVARCHAR(200) NOT NULL,
    ContentType  VARCHAR(100)  NOT NULL,
    SizeBytes    INT NOT NULL,
    UploadedBy   INT NOT NULL CONSTRAINT FK_Attachments_Users REFERENCES dbo.Users (UserId),
    UploadedAt   DATETIME2(0) NOT NULL CONSTRAINT DF_Attachments_UploadedAt DEFAULT SYSUTCDATETIME()
);
GO

-- ---------------------------------------------------------------- Escalations
-- One record per complaint per reason, so the timer never escalates the same thing twice.
IF OBJECT_ID(N'dbo.Escalations', N'U') IS NULL
CREATE TABLE dbo.Escalations (
    EscalationId INT IDENTITY(1,1) CONSTRAINT PK_Escalations PRIMARY KEY,
    ComplaintId  INT NOT NULL CONSTRAINT FK_Escalations_Complaints REFERENCES dbo.Complaints (ComplaintId),
    Reason       VARCHAR(20) NOT NULL CONSTRAINT CK_Escalations_Reason CHECK (Reason IN ('overdue', 'critical')),
    Details      NVARCHAR(300) NULL,
    CreatedAt    DATETIME2(0) NOT NULL CONSTRAINT DF_Escalations_CreatedAt DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Escalations_Complaint_Reason UNIQUE (ComplaintId, Reason)
);
GO

-- -------------------------------------------------------------- Notifications
IF OBJECT_ID(N'dbo.Notifications', N'U') IS NULL
CREATE TABLE dbo.Notifications (
    NotificationId INT IDENTITY(1,1) CONSTRAINT PK_Notifications PRIMARY KEY,
    UserId         INT NOT NULL CONSTRAINT FK_Notifications_Users REFERENCES dbo.Users (UserId),
    ComplaintId    INT NULL CONSTRAINT FK_Notifications_Complaints REFERENCES dbo.Complaints (ComplaintId),
    Type           VARCHAR(30)   NOT NULL,
    Message        NVARCHAR(300) NOT NULL,
    IsRead         BIT NOT NULL CONSTRAINT DF_Notifications_IsRead DEFAULT 0,
    CreatedAt      DATETIME2(0) NOT NULL CONSTRAINT DF_Notifications_CreatedAt DEFAULT SYSUTCDATETIME()
);
GO

-- -------------------------------------------------------------------- Indexes
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_Assignments_Current' AND object_id = OBJECT_ID(N'dbo.Assignments'))
CREATE UNIQUE INDEX UX_Assignments_Current ON dbo.Assignments (ComplaintId) WHERE IsCurrent = 1;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Assignments_Staff' AND object_id = OBJECT_ID(N'dbo.Assignments'))
CREATE INDEX IX_Assignments_Staff ON dbo.Assignments (StaffId, IsCurrent);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Complaints_Student' AND object_id = OBJECT_ID(N'dbo.Complaints'))
CREATE INDEX IX_Complaints_Student ON dbo.Complaints (StudentId, CreatedAt DESC);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Complaints_Status_Due' AND object_id = OBJECT_ID(N'dbo.Complaints'))
CREATE INDEX IX_Complaints_Status_Due ON dbo.Complaints (Status, DueAt);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_StatusHistory_Complaint' AND object_id = OBJECT_ID(N'dbo.StatusHistory'))
CREATE INDEX IX_StatusHistory_Complaint ON dbo.StatusHistory (ComplaintId, ChangedAt);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Attachments_Complaint' AND object_id = OBJECT_ID(N'dbo.Attachments'))
CREATE INDEX IX_Attachments_Complaint ON dbo.Attachments (ComplaintId);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Notifications_User' AND object_id = OBJECT_ID(N'dbo.Notifications'))
CREATE INDEX IX_Notifications_User ON dbo.Notifications (UserId, IsRead, CreatedAt DESC);
GO
