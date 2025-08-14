def cleanup_out_files(context):
    for file_path in context.cleanup_out_files:
        try:
            if file_path.exists():
                file_path.unlink()
        except FileNotFoundError:
            print(f"File not found on cleanup: {file_path}")
