-- Gives the Function App's managed identity the database permissions it needs. Run it ONCE, as the SQL admin.
--
-- 1. Replace <function-app-name> below with the exact name of your Function App (keep the square brackets).
-- 2. Run it in the Azure portal: your database -> Query editor, signed in with Microsoft Entra (you are the SQL admin).
--
-- Why these roles: db_datareader / db_datawriter = read and write the tables. The sequence permission lets the app
-- take the next complaint number. The app never needs to create or drop tables (init_db.py does that, as you).
CREATE USER [<function-app-name>] FROM EXTERNAL PROVIDER;
GO
ALTER ROLE db_datareader ADD MEMBER [<function-app-name>];
ALTER ROLE db_datawriter ADD MEMBER [<function-app-name>];
GRANT UPDATE ON OBJECT::dbo.ComplaintNumberSeq TO [<function-app-name>];
GO
