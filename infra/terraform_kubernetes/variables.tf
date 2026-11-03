
variable "yc_config" {
  description = "Yandex Cloud configuration"

  type = object({
    cloud_id  = string
    folder_id = string
    zone      = string
  })
}

variable "network_id" {
  description = "VPC ID from Foundation"
  type        = string
}

variable "subnet_id" {
  description = "App subnet ID from Foundation"
  type        = string
}

variable "registry_folder_id" {
  description = "Folder containing Docker images"
  type        = string
}

variable "node_cpu" {
  type    = number
  default = 2
}

variable "node_memory" {
  type    = number
  default = 6
}

variable "node_core_fraction" {
  type    = number
  default = 50
}
