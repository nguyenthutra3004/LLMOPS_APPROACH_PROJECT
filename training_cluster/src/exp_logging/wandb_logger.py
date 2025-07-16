import os
import wandb
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from .base_logger import BaseLogger
import datetime
import logging

class WandbLogger(BaseLogger):
    """Weights & Biases implementation of BaseLogger."""
    
    def __init__(self, model_name: str = None, lora_name: str = None):
        
        super().__init__(model_name=model_name, lora_name=lora_name)

        self.run = None
        self._api_key = os.getenv("WANDB_API_KEY")
        self.project = os.getenv("WANDB_PROJECT")
        self.entity = os.getenv("WANDB_ENTITY")
        self.tracking_backend = "wandb"
        wandb.login(key=self._api_key)

        self.config = {}
        
    def login(self, **kwargs):
        """Login to WandB."""
        key = kwargs.get('key', self.api_key)
        wandb.login(key=key)
        
    def init_run(self, project: str = None, entity: str = None, job_type: str = "experiment", 
                 config: Dict[str, Any] = {}, name: Optional[str] = None, run_id = None) -> Any:
        """Initialize a new WandB run."""
        
        self.update_config(config)

        if 'model_name' in config:
            self.model_name = config['model_name']
        if 'lora_name' in config:
            self.lora_name = config['lora_name']
        if 'save_name' in config:
            self.save_name = config['save_name']
        else:
            self.save_name = config.get('lora_name', self.lora_name)


        if self.run is not None or self.run_id is not None:
            logging.warning("Run already initialized. Please finish the current run before starting a new one.")
            return self.run


        if project:
            self.project = project
        if entity:
            self.entity = entity
        if job_type:
            self.job_type = job_type
        if config:
            self.config = config

        
        if run_id:
            logging.info(f"Resuming run with ID: {run_id}")
            self.run = wandb.init(
                id=run_id,
                resume="allow",
            )
        else:
            self.run = wandb.init(
                project=project or self.project,
                entity=entity or self.entity,
                job_type=job_type,
                config=config,
                name=name
            )
        self.run_name = self.run.name
        return self.run
    
    def auto_init_run(self, config = None):
        """Automatically initialize a WandB run with default parameters."""
        project = os.getenv("WANDB_PROJECT", "training")
        
        config = config or {}

        self.init_run(
            project=project,
            config=config,
            name=f"{project}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    def log_metric(self, key: str, value: Union[float, int]) -> None:
        """Log a single metric to WandB."""
        if not self.check_run_status():
            return
        self.run.log({key: value})
        
    def log_metrics(self, metrics: Dict[str, Union[float, int]]) -> None:
        
        
        """Log multiple metrics to WandB."""
        if not self.check_run_status():
            return
        self.run.log(metrics)
    
    def log_table(self, key: str, dataframe: pd.DataFrame) -> None:
        """Log a dataframe as a table to WandB."""
        if not self.check_run_status():
            return
        
        table = wandb.Table(dataframe=dataframe)
        self.run.log({key: table})
    
    def log_artifact(self, local_path: str, name: Optional[str] = None, type_ = "file" ) -> None:
        """Log an artifact file to WandB."""
        if not self.check_run_status():
            return
        
        artifact = wandb.Artifact(name=name or os.path.basename(local_path), type = type_)
        artifact.add_file(local_path)
        self.run.log_artifact(artifact)

        return f"{self.entity}/{self.project}/{artifact.name}"

        
    def update_summary(self, key: str, value: Any) -> None:
        """Update a summary metric in WandB."""
        if not self.check_run_status():
            return
        
        self.run.summary[key] = value
    
    def finish_run(self) -> None:
        """End the current WandB run."""
        if self.run:
            self.run.finish()
            self.run = None
            self.run_id = None

    def get_tracking_url(self) -> Optional[str]:
        """Get URL to the current run in WandB UI."""
        if not self.check_run_status():
            return
        
        if self.run:
            return self.run.get_url()
        return None
    
    def register_model(self, model_path: str, model_name: str, collection_name: str = None, 
                  registry_name: str = "model", **kwargs) -> Optional[str]:
       
        if not self.check_run_status():
            return
            
        try:
            # Log the model as an artifact
            model_artifact = self.run.log_artifact(
                artifact_or_path=model_path,
                name=model_name,
                type="model"
            )
            
            # Link to the registry using the prescribed format
            if collection_name:
                registry_path = f"wandb-registry-{registry_name}/{collection_name}"
                self.run.link_artifact(
                    artifact=model_artifact,
                    target_path=registry_path,
                )
                print(f"Model registered at: {registry_path}")
                
                # Update summary with model registration info
                self.update_summary("registered_model", registry_path)
                self.log_metric("model_registered", 1.0)
                
                return registry_path
            else:
                print("Model artifact created but not registered (no collection_name provided)")
                return model_artifact.name
                
        except Exception as e:
            print(f"Error registering model: {str(e)}")
            return None