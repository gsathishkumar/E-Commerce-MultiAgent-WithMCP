# Use an official Python runtime as a base image
FROM python:3.13-slim

# Create a non-root user and switch to it
RUN useradd -m appuser
RUN mkdir -p /product_rag_app
RUN chown appuser /product_rag_app
USER appuser

# Ensure user-level pip installs are on PATH (pip runs as non‑root below)
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Set the working directory in the container
WORKDIR /product_rag_app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies for appuser into home dir
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application code into the container
COPY --chown=appuser:appuser . .

# Expose the port your app runs on
EXPOSE 8000

# Specify the command to run when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
