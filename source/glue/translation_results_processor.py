import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, explode, lit, from_json
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, DoubleType

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME', 
    'execution_id', 
    'caller_id', 
    'input_bucket', 
    'output_bucket',
    'quality_control_path',
    'quality_estimation_path',
    'output_path'
])

# Initialize Spark and Glue contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read JSONL file (translation results)
quality_control_path = f"s3://{args['input_bucket']}/{args['quality_control_path']}"
print(f"Reading quality control data from: {quality_control_path}")
df_jsonl = spark.read.option("recursiveFileLookup", "true").json(quality_control_path).filter(col("_metadata.file_path").rlike(".*\\.jsonl$"))

# Read JSON file (scores)
quality_estimation_path = args['quality_estimation_path']
print(f"Reading quality estimation data from: {quality_estimation_path}")

# Define schema for the JSON file
schema = StructType([
    StructField("predictions", ArrayType(
        StructType([
            StructField("recordId", StringType(), True),
            StructField("score", DoubleType(), True)
        ])
    ), True)
])

df_json = spark.read.option("multiline", "true").schema(schema).json(quality_estimation_path)

# Explode the predictions array to get individual records
df_scores = df_json.select(explode(col("predictions")).alias("prediction")) \
                  .select(col("prediction.recordId").alias("recordId"), 
                         col("prediction.score").alias("score"))

# Join JSONL data with scores by recordId
df_combined = df_jsonl.join(df_scores, "recordId", "left")

# Write the combined data as JSONL
output_path = f"s3://{args['output_bucket']}/{args['output_path']}"
print(f"Writing processed data to: {output_path}")
df_combined.write.mode("overwrite").json(output_path)

# End the job
job.commit()