
variable "yc_config" {
  description = "Yandex Cloud configuration"

  type = object({
    cloud_id  = string
    folder_id = string
    zone      = string
  })
}

variable "network_name" {
  description = "Name of the project VPC"
  type        = string
  default     = "taxi-ml-network"
}

variable "subnets" {
  description = "Project subnets"

  type = map(object({
    name = string
    cidr = string
  }))

  default = {
    app = {
      name = "taxi-app-subnet"
      cidr = "10.10.1.0/24"
    }

    services = {
      name = "taxi-services-subnet"
      cidr = "10.10.2.0/24"
    }
  }
}
