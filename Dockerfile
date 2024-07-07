FROM quay.io/astronomer/astro-runtime:11.6.0

# install soda into a virtual environment
RUN python -m venv soda_venv && source soda_venv/bin/activate && \
    pip install --no-cache-dir soda-core-bigquery==3.0.45 &&\
    pip install --no-cache-dir google-cloud-bigquery-storage &&\
    pip install --no-cache-dir soda-core-scientific==3.0.45 && deactivate

# install dbt into a virtual environment
RUN python -m venv dbt_venv && source dbt_venv/bin/activate && \
    pip install --no-cache-dir google-cloud-bigquery-storage &&\
    pip install --no-cache-dir dbt-bigquery==1.5.3 && deactivate

# install pandas into a virtual environment
RUN python -m venv pandas_venv && source pandas_venv/bin/activate && \
    pip install --no-cache-dir pandas && deactivate