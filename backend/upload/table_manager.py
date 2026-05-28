import openpyxl
from io import BytesIO
from django.db import connection
from django.utils.text import slugify
from datetime import datetime
import re
import openai
import json
import os


def sanitize_column_name(name):
    """Convert column name to valid SQL identifier"""
    # Remove special chars, replace spaces with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip())
    # Ensure doesn't start with number
    if sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"
    return sanitized[:63]  # SQLite limit


def generate_table_name(user_id, filename):
    """Generate unique table name from user_id and filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(filename.replace('.xlsx', '').replace('.xls', ''))[:30]
    table_name = f"user_{user_id}_{slug}_{timestamp}"
    return table_name.lower()


def map_ai_type_to_sql(ai_type):
    """Map AI detected types to SQL datatypes"""
    type_mapping = {
        "INTEGER": "INTEGER",
        "DECIMAL": "REAL",
        "DATE": "DATE",
        "EMAIL": "TEXT",
        "TEXT": "TEXT"
    }
    return type_mapping.get(ai_type, "TEXT")


def create_table_from_schema(table_name, schema, column_names):
    """
    Create a physical table in the database
    
    Args:
        table_name: Name of the table to create
        schema: Dict mapping column_name -> AI_TYPE
        column_names: List of column names in order
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Build CREATE TABLE statement
        columns_sql = []
        for col_name in column_names:
            if col_name in schema:
                sanitized_col = sanitize_column_name(col_name)
                sql_type = map_ai_type_to_sql(schema[col_name])
                # Quote column name to be safe for SQL identifiers
                quoted_col = connection.ops.quote_name(sanitized_col)
                columns_sql.append(f"{quoted_col} {sql_type}")
        
        # Add id and timestamps
        columns_definition = ", ".join([
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            *columns_sql,
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ])
        
        # Quote table name to avoid syntax errors for characters like '-'
        quoted_table = connection.ops.quote_name(table_name)

        create_table_sql = f"CREATE TABLE {quoted_table} ({columns_definition})"

        with connection.cursor() as cursor:
            cursor.execute(create_table_sql)
        
        return True
    except Exception as e:
        print(f"Error creating table: {e}")
        return False


def insert_excel_data_into_table(table_name, file, column_names, schema):
    """
    Read Excel file and insert data into the created table
    
    Args:
        table_name: Name of the table
        file: File object from request
        column_names: List of column names
        schema: Dict mapping column_name -> AI_TYPE
    
    Returns:
        dict: {
            "success": bool,
            "rows_inserted": int,
            "error": str (if any)
        }
    """
    try:
        # Load workbook
        file.seek(0)
        wb = openpyxl.load_workbook(BytesIO(file.read()))
        ws = wb.active
        
        # Prepare sanitized and quoted column names
        sanitized_cols = [sanitize_column_name(col) for col in column_names]
        quoted_cols = [connection.ops.quote_name(c) for c in sanitized_cols]
        
        # Insert rows
        rows_inserted = 0
        
        with connection.cursor() as cursor:
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                # Skip empty rows
                if all(cell is None or str(cell).strip() == "" for cell in row):
                    continue
                
                # Build INSERT statement
                placeholders = ", ".join(["%s" for _ in sanitized_cols])
                # Quote table and column names for safe insertion
                quoted_table = connection.ops.quote_name(table_name)
                insert_sql = f"INSERT INTO {quoted_table} ({', '.join(quoted_cols)}) VALUES ({placeholders})"

                # Prepare values with type conversion
                values = []
                for col_idx, col_name in enumerate(column_names):
                    cell_value = row[col_idx] if col_idx < len(row) else None
                    
                    if cell_value is None or str(cell_value).strip() == "":
                        values.append(None)
                    else:
                        ai_type = schema.get(col_name)
                        
                        # Type conversion based on schema
                        if ai_type == "INTEGER":
                            try:
                                values.append(int(cell_value))
                            except (ValueError, TypeError):
                                values.append(str(cell_value))
                        
                        elif ai_type == "DECIMAL":
                            try:
                                values.append(float(cell_value))
                            except (ValueError, TypeError):
                                values.append(str(cell_value))
                        
                        elif ai_type == "DATE":
                            if isinstance(cell_value, datetime):
                                values.append(cell_value.strftime("%Y-%m-%d"))
                            else:
                                values.append(str(cell_value))
                        
                        else:  # EMAIL, TEXT
                            values.append(str(cell_value).strip())
                
                try:
                    cursor.execute(insert_sql, tuple(values))
                    rows_inserted += 1
                except Exception as e:
                    # Log but continue (one bad row shouldn't stop everything)
                    print(f"Error inserting row {row_num}: {e}")
                    continue
        
        return {
            "success": True,
            "rows_inserted": rows_inserted
        }
    
    except Exception as e:
        return {
            "success": False,
            "rows_inserted": 0,
            "error": str(e)
        }


def drop_table(table_name):
    """Drop a dynamically created table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        return True
    except Exception as e:
        print(f"Error dropping table: {e}")
        return False


def get_table_structure(table_name):
    """
    Get the structure of a table (column names and types)
    
    Args:
        table_name: Name of the table
    
    Returns:
        dict: {
            "columns": [{"name": "col_name", "type": "TEXT/INTEGER/..."}],
            "error": str (if any)
        }
    """
    try:
        # Quote the table name to avoid syntax errors for names with special chars (e.g. hyphens)
        quoted_table = connection.ops.quote_name(table_name)

        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info({quoted_table})")
            columns = cursor.fetchall()

        structure = []
        for col in columns:
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            structure.append({
                "name": col[1],
                "type": col[2]
            })

        return {
            "success": True,
            "columns": structure
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def generate_sql_from_prompt(table_name, schema_columns, user_prompt):
    """
    Use OpenAI to generate SQL query from natural language prompt
    
    Args:
        table_name: Name of the table to query
        schema_columns: List of dicts with 'name' and 'type' keys
        user_prompt: Natural language query from user
    
    Returns:
        dict: {
            "success": bool,
            "sql": str (generated SQL query),
            "error": str (if any)
        }
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "OpenAI API key not configured"
            }
        
        # Build schema description for OpenAI
        columns_desc = "\n".join([f"- {col['name']} ({col['type']})" for col in schema_columns])
        
        system_prompt = f"""You are a SQL query generator. Generate ONLY a valid SQLite SELECT query based on the user's natural language request.

Table name: {table_name}
Table structure:
{columns_desc}

Rules:
1. Generate ONLY the SELECT query, nothing else
2. Use proper SQLite syntax
3. Quote table and column names with backticks
4. If the user asks for COUNT, use COUNT(*)
5. Handle aggregations like SUM, AVG, MAX, MIN properly
6. If user asks to filter/search, use WHERE clause
7. Do not use LIMIT unless the user explicitly asks for a specific number of rows
8. Return results in a readable format

Respond with ONLY the SQL query, no explanations."""

        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        generated_sql = response.choices[0].message.content.strip()
        
        # Clean up the SQL if it's wrapped in markdown code blocks
        if generated_sql.startswith("```"):
            generated_sql = generated_sql.split("```")[1]
            if generated_sql.startswith("sql"):
                generated_sql = generated_sql[3:]
            generated_sql = generated_sql.strip()
        
        return {
            "success": True,
            "sql": generated_sql
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate SQL: {str(e)}"
        }


def execute_query(sql_query):
    """
    Safely execute a SELECT query and return results
    
    Args:
        sql_query: SQL query to execute
    
    Returns:
        dict: {
            "success": bool,
            "columns": [col_names],
            "rows": [[row_data]],
            "row_count": int,
            "error": str (if any)
        }
    """
    try:
        # Security check: ensure it's a SELECT query
        if not sql_query.strip().upper().startswith("SELECT"):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed"
            }
        
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        
        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Query execution failed: {str(e)}"
        }
