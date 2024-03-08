# Entrance paramns
YEAR=$1
MONTH=$2

# Paths
URL="https://s3.amazonaws.com/tripdata/JC-${YEAR}${MONTH}-citibike-tripdata.csv.zip"
dir_to_download="${AIRFLOW_HOME}/include/dataset/raw/${YEAR}/${MONTH}"
FILE_NAME="JC-${YEAR}${MONTH}-citibike-tripdata.csv"
LOCAL_PATH="${dir_to_download}/${FILE_NAME}.zip"


# Code
echo "\nDownloading citibike dataset from ${YEAR}/${MONTH}"

mkdir -p ${dir_to_download}
curl -o ${LOCAL_PATH} ${URL} || exit 1
unzip ${LOCAL_PATH} -d ${dir_to_download}
rm -r ${dir_to_download}/__MACOSX ${LOCAL_PATH}
zip -m ${LOCAL_PATH} ${dir_to_download}/${FILE_NAME}

echo "\nDownload completed successfully!"

# Return value:
echo "${LOCAL_PATH}"