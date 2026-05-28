from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UploadSerializer
from .validators import validate_excel_upload
from .models import TableSchema
from .table_manager import (
    generate_table_name, 
    create_table_from_schema, 
    insert_excel_data_into_table,
    get_table_structure,
    generate_sql_from_prompt,
    execute_query
)

class ExcelUploadView(APIView):
    permission_classes = [IsAuthenticated]  # JWT protects this

    def post(self, request):

        # Step 1 — check file extension via serializer
        serializer = UploadSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=400)

        # Step 2 — validate content (headers + empty cells)
        file = request.FILES.get("upload_file")
        result = validate_excel_upload(file)

        if not result["valid"]:
            return Response({
                "success": False,
                "errors": result["errors"]
            }, status=422)

        # Step 3 — rewind and save upload record
        file.seek(0)
        upload = serializer.save()
        
        # Store schema in upload
        schema = result.get("schema", {})
        column_names = result.get("column_names", [])
        upload.schema = schema
        upload.is_valid = True
        upload.save()

        # Step 4 — Generate table name and create table
        table_name = generate_table_name(request.user.id, upload.original_filename)
        print(table_name, schema, column_names)
        table_created = create_table_from_schema(table_name, schema, column_names)
        
        if not table_created:
            return Response({
                "success": False,
                "error": "Failed to create table for this schema"
            }, status=500)

        # Step 5 — Insert data into the table
        file.seek(0)
        insert_result = insert_excel_data_into_table(table_name, file, column_names, schema)
        
        if not insert_result["success"]:
            return Response({
                "success": False,
                "error": f"Failed to insert data: {insert_result.get('error', 'Unknown error')}"
            }, status=500)

        # Step 6 — Create TableSchema record to track the table
        table_schema = TableSchema.objects.create(
            user=request.user,
            table_name=table_name,
            schema=schema,
            column_names=column_names
        )
        
        # Link upload to table schema
        upload.table_schema = table_schema
        upload.rows_inserted = insert_result["rows_inserted"]
        upload.save()

        return Response({
            "success": True,
            "upload_id": upload.id,
            "filename": upload.original_filename,
            "table_name": table_name,
            "schema": schema,
            "rows_inserted": insert_result["rows_inserted"]
        }, status=201)


class QueryTableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handle natural language queries on uploaded tables
        
        Expected request data:
        {
            "table_name": "user_123_filename_...",
            "query_prompt": "Show me all rows where...",
            "upload_id": 42  # optional, for convenience
        }
        """
        table_name = request.data.get("table_name")
        query_prompt = request.data.get("query_prompt", "").strip()
        upload_id = request.data.get("upload_id")

        # Validate inputs
        if not table_name and not upload_id:
            return Response({
                "success": False,
                "error": "Either table_name or upload_id is required"
            }, status=400)

        if not query_prompt:
            return Response({
                "success": False,
                "error": "query_prompt is required"
            }, status=400)

        # If upload_id provided, get table_name from it
        if upload_id and not table_name:
            try:
                from .models import Upload
                upload = Upload.objects.get(id=upload_id, user=request.user)
                if not upload.table_schema:
                    return Response({
                        "success": False,
                        "error": "Upload does not have an associated table"
                    }, status=404)
                table_name = upload.table_schema.table_name
            except Exception as e:
                return Response({
                    "success": False,
                    "error": f"Upload not found: {str(e)}"
                }, status=404)

        # Verify table belongs to this user
        try:
            table_schema = TableSchema.objects.get(table_name=table_name, user=request.user)
        except TableSchema.DoesNotExist:
            return Response({
                "success": False,
                "error": "Table not found or access denied"
            }, status=404)

        # Step 1: Get table structure
        struct_result = get_table_structure(table_name)
        if not struct_result.get("success"):
            return Response({
                "success": False,
                "error": f"Failed to get table structure: {struct_result.get('error')}"
            }, status=500)

        schema_columns = struct_result.get("columns", [])

        # Step 2: Generate SQL from natural language using OpenAI
        sql_result = generate_sql_from_prompt(table_name, schema_columns, query_prompt)
        if not sql_result.get("success"):
            return Response({
                "success": False,
                "error": sql_result.get("error", "Failed to generate SQL")
            }, status=500)

        generated_sql = sql_result.get("sql")

        # Step 3: Execute the generated SQL
        exec_result = execute_query(generated_sql)
        if not exec_result.get("success"):
            return Response({
                "success": False,
                "error": exec_result.get("error", "Failed to execute query")
            }, status=500)

        # Step 4: Return formatted results
        return Response({
            "success": True,
            "query_prompt": query_prompt,
            "generated_sql": generated_sql,
            "columns": exec_result.get("columns", []),
            "rows": exec_result.get("rows", []),
            "row_count": exec_result.get("row_count", 0)
        }, status=200)