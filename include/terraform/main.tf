# Adding google provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.18.0"
    }
  }
}

provider "google" {
  project = "project-datapipeline-airflow"
  region  = "us-central1"
}

# Creating google storage bucket
# resource "google_storage_bucket" "my-bucket" {
#   count                    = var.create_bucket ? 1 : 0
#   name                     = "pda-data-pipeline-bucket"
#   location                 = "US"
#   force_destroy            = true
#   public_access_prevention = "enforced"

#   lifecycle_rule {
#     condition {
#       age = 1
#     }
#     action {
#       type = "AbortIncompleteMultipartUpload"
#     }
#   }
# }

resource "google_storage_bucket_object" "folder_with_dags" {
  for_each = fileset("../dags", "**/*")

  name   = "dags/${each.value}"
  source = "../dags/${each.value}"
  bucket = "pda-data-pipeline-bucket"
}