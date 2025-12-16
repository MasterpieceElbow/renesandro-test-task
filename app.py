try:
    1 / 0

except Exception as e:
    raise e.__class__(f"An error occurred during division: {str(e)}")