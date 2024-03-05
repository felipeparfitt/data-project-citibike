bold=$(tput bold)
normal=$(tput sgr0)

local_dir=$(pwd)

echo "Starting local tests...\n"


echo "\n Starting Flake8 test..."
python3 -m flake8 --ignore E501 dags --benchmark || exit 1

echo "\n Starting Black test..."
python3 -m  black --check dags/ -v || exit 1

echo "\n Starting Pytest tests..."
cd tests/dags/ || exit 1
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests.py -v && rm -rf .pytest_cache || { rm -rf .pytest_cache && exit 1; }  #
#rm -rf .pytest_cache
cd "$local_dir" || exit 1

echo "\n Starting JSON validation tests..."
python3 -m json.tool include/airflow_variables/variables.json || exit 1


echo "${bold}\nAll tests completed successfully!"