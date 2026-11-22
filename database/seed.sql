-- Reference data: departments and complaint categories. Safe to run more than once.
-- Contains no users and no passwords (demo users are created by init_db.py --demo-users).
SET NOCOUNT ON;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'Electrical')
    INSERT INTO dbo.Departments (Name) VALUES (N'Electrical');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'Plumbing & Water')
    INSERT INTO dbo.Departments (Name) VALUES (N'Plumbing & Water');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'IT & Network')
    INSERT INTO dbo.Departments (Name) VALUES (N'IT & Network');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'Housekeeping')
    INSERT INTO dbo.Departments (Name) VALUES (N'Housekeeping');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'Civil & Carpentry')
    INSERT INTO dbo.Departments (Name) VALUES (N'Civil & Carpentry');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WHERE Name = N'Security & Safety')
    INSERT INTO dbo.Departments (Name) VALUES (N'Security & Safety');
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Electrical fault')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Electrical fault', DepartmentId, 'High', N'power,electric,switch,socket,light,streetlight,fan,bulb,wiring,mcb,flicker,projector' FROM dbo.Departments WHERE Name = N'Electrical';
IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Water & plumbing')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Water & plumbing', DepartmentId, 'Medium', N'water,leak,tap,pipe,drain,toilet,flush,geyser,overflow,cooler,seepage' FROM dbo.Departments WHERE Name = N'Plumbing & Water';
IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Wi-Fi & computers')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Wi-Fi & computers', DepartmentId, 'Medium', N'wifi,wi fi,internet,network,router,computer,system,login,lan,booting' FROM dbo.Departments WHERE Name = N'IT & Network';
IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Cleanliness & waste')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Cleanliness & waste', DepartmentId, 'Low', N'dirty,garbage,waste,dustbin,bin,clean,smell,pest,cockroach,litter,mosquito' FROM dbo.Departments WHERE Name = N'Housekeeping';
IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Furniture & civil work')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Furniture & civil work', DepartmentId, 'Low', N'bench,chair,desk,door,window,crack,ceiling,wall,plaster,roof,lock,handle' FROM dbo.Departments WHERE Name = N'Civil & Carpentry';
IF NOT EXISTS (SELECT 1 FROM dbo.Categories WHERE Name = N'Safety & security')
    INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords)
    SELECT N'Safety & security', DepartmentId, 'High', N'cctv,security,theft,unsafe,gate,guard,stray,alarm,extinguisher,gas' FROM dbo.Departments WHERE Name = N'Security & Safety';
GO
