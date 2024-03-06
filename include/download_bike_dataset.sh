# Entrance paramns
YEAR=$1
MONTH=$2
URL="https://s3.amazonaws.com/tripdata/JC-${YEAR}${MONTH}-citibike-tripdata.csv.zip"
dir_to_download="${AIRFLOW_HOME}/include/dataset/raw/${YEAR}/${MONTH}"
LOCAL_PATH="${dir_to_download}/JC-${YEAR}${MONTH}-citibike-tripdata.csv.zip"


echo "\nDownloading citibike dataset from ${YEAR}/${MONTH}"

mkdir -p ${dir_to_download}
curl -o ${LOCAL_PATH} ${URL} || exit 1

echo "\nDownload completed successfully!"