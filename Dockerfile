FROM python:3.13-slim
# Set Qt to minimal platform for headless operation
ENV QT_QPA_PLATFORM=minimal

# Set working directory
WORKDIR /app


# Copy application files
COPY DerivativeMill/ ./DerivativeMill/
COPY DerivativeMill/Resources ./DerivativeMill/Resources
COPY DerivativeMill/Input ./DerivativeMill/Input
COPY DerivativeMill/Output ./DerivativeMill/Output
COPY DerivativeMill/Section_232_Actions.csv ./DerivativeMill/Section_232_Actions.csv
COPY DerivativeMill/Section_232_Tariffs_Compiled.csv ./DerivativeMill/Section_232_Tariffs_Compiled.csv
COPY DerivativeMill/shipment_mapping.json ./DerivativeMill/shipment_mapping.json
COPY DerivativeMill/column_mapping.json ./DerivativeMill/column_mapping.json
COPY DerivativeMill/README.md ./DerivativeMill/README.md
COPY DerivativeMill/Resources/References ./DerivativeMill/Resources/References


# Install system dependencies for PyQt5
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 libx11-xcb1 libxcb1 libx11-6 libxext6 libxrender1 libxi6 libsm6 libxrandr2 libfontconfig1

# Install dependencies
RUN pip install --no-cache-dir pandas openpyxl PyQt5

# Set default command (replace with your CLI entrypoint if needed)
CMD ["python", "DerivativeMill/derivativemill.py"]
