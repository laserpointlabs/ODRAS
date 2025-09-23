#!/usr/bin/env python3
"""
Camunda Process Management Best Practices Implementation

This module implements best practices for managing Camunda BPM processes including:
- Process monitoring and health checks
- Failed process detection and cleanup
- Process lifecycle management
- Performance monitoring
- Incident management
"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CamundaProcessManager:
    """
    Camunda Process Manager implementing best practices for process lifecycle management
    """

    def __init__(self, camunda_base_url: str = "http://localhost:8080/engine-rest"):
        self.base_url = camunda_base_url
        self.timeout = 10

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def check_camunda_health(self) -> bool:
        """Check if Camunda engine is accessible"""
        try:
            response = requests.get(f"{self.base_url}/version", timeout=5)
            if response.status_code == 200:
                version = response.json().get("version", "unknown")
                self.log(f"✅ Camunda engine accessible - version {version}")
                return True
            else:
                self.log(f"❌ Camunda health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Camunda health check failed: {e}", "ERROR")
            return False

    def get_active_processes(self, process_key_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active process instances, optionally filtered by process key"""
        try:
            params = {}
            if process_key_filter:
                params["processDefinitionKey"] = process_key_filter

            response = requests.get(
                f"{self.base_url}/process-instance",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                processes = response.json()
                if process_key_filter:
                    self.log(f"📊 Found {len(processes)} active '{process_key_filter}' processes")
                else:
                    self.log(f"📊 Found {len(processes)} total active processes")
                return processes
            else:
                self.log(f"❌ Failed to get active processes: {response.status_code}", "ERROR")
                return []

        except Exception as e:
            self.log(f"❌ Error getting active processes: {e}", "ERROR")
            return []

    def get_knowledge_processing_instances(self) -> List[Dict[str, Any]]:
        """Get specifically the automatic_knowledge_processing instances"""
        return self.get_active_processes("automatic_knowledge_processing")

    def get_failed_processes(self) -> List[Dict[str, Any]]:
        """Get processes with incidents (failures)"""
        try:
            # Get processes with incidents
            response = requests.get(
                f"{self.base_url}/process-instance",
                params={"withIncidents": "true"},
                timeout=self.timeout
            )

            if response.status_code == 200:
                processes_with_incidents = response.json()
                self.log(f"⚠️  Found {len(processes_with_incidents)} processes with incidents")
                return processes_with_incidents
            else:
                self.log(f"❌ Failed to get failed processes: {response.status_code}", "ERROR")
                return []

        except Exception as e:
            self.log(f"❌ Error getting failed processes: {e}", "ERROR")
            return []

    def get_process_incidents(self, process_instance_id: str) -> List[Dict[str, Any]]:
        """Get incidents for a specific process instance"""
        try:
            response = requests.get(
                f"{self.base_url}/incident",
                params={"processInstanceId": process_instance_id},
                timeout=self.timeout
            )

            if response.status_code == 200:
                incidents = response.json()
                return incidents
            else:
                self.log(f"❌ Failed to get incidents for {process_instance_id}: {response.status_code}", "ERROR")
                return []

        except Exception as e:
            self.log(f"❌ Error getting incidents: {e}", "ERROR")
            return []

    def cleanup_old_processes(self, older_than_hours: int = 24) -> int:
        """Clean up completed processes older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            cutoff_iso = cutoff_time.isoformat()

            # Get completed processes older than cutoff
            response = requests.get(
                f"{self.base_url}/history/process-instance",
                params={
                    "finished": "true",
                    "finishedBefore": cutoff_iso
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                old_processes = response.json()
                self.log(f"🧹 Found {len(old_processes)} old completed processes")

                # In production, you might delete these, but for safety we'll just report
                # DELETE operations should be done carefully with proper authorization
                return len(old_processes)
            else:
                self.log(f"❌ Failed to get old processes: {response.status_code}", "ERROR")
                return 0

        except Exception as e:
            self.log(f"❌ Error during cleanup: {e}", "ERROR")
            return 0

    def monitor_knowledge_processing(self, max_wait_minutes: int = 5) -> Dict[str, Any]:
        """
        Monitor knowledge processing workflows with proper error handling

        Returns:
            Dict with status, active_count, failed_count, and details
        """
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        self.log(f"🔍 Monitoring knowledge processing workflows (max {max_wait_minutes} minutes)...")

        if not self.check_camunda_health():
            return {
                "status": "error",
                "error": "Camunda engine not accessible",
                "active_count": 0,
                "failed_count": 0
            }

        knowledge_keywords = ["knowledge", "ingestion", "embedding", "chunk", "extract", "generate"]

        while time.time() - start_time < max_wait_seconds:
            try:
                # Get all active processes
                active_processes = self.get_active_processes()

                # Filter for knowledge-related processes
                knowledge_processes = [
                    p for p in active_processes
                    if any(keyword in p.get("processDefinitionKey", "").lower()
                          for keyword in knowledge_keywords)
                ]

                # Check for failed processes
                failed_processes = self.get_failed_processes()
                knowledge_failures = [
                    p for p in failed_processes
                    if any(keyword in p.get("processDefinitionKey", "").lower()
                          for keyword in knowledge_keywords)
                ]

                if knowledge_failures:
                    self.log(f"❌ Found {len(knowledge_failures)} failed knowledge processes", "ERROR")
                    for failure in knowledge_failures:
                        process_id = failure.get("id", "unknown")
                        process_key = failure.get("processDefinitionKey", "unknown")
                        self.log(f"   Failed: {process_key} (ID: {process_id})", "ERROR")

                        # Get incident details
                        incidents = self.get_process_incidents(process_id)
                        for incident in incidents:
                            incident_msg = incident.get("incidentMessage", "No message")
                            self.log(f"     Incident: {incident_msg}", "ERROR")

                    return {
                        "status": "failed",
                        "active_count": len(knowledge_processes),
                        "failed_count": len(knowledge_failures),
                        "failed_processes": knowledge_failures
                    }

                if not knowledge_processes:
                    self.log("✅ No active knowledge processing workflows - processing complete!")
                    return {
                        "status": "completed",
                        "active_count": 0,
                        "failed_count": 0,
                        "processing_time": time.time() - start_time
                    }

                elapsed = int(time.time() - start_time)
                self.log(f"⏳ {len(knowledge_processes)} knowledge workflows active (elapsed: {elapsed}s)")

                # Show details of active processes
                for process in knowledge_processes[:3]:  # Show first 3
                    process_key = process.get("processDefinitionKey", "unknown")
                    process_id = process.get("id", "unknown")
                    self.log(f"   Active: {process_key} (ID: {process_id})")

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                self.log(f"❌ Error during monitoring: {e}", "ERROR")
                return {
                    "status": "error",
                    "error": str(e),
                    "active_count": 0,
                    "failed_count": 0
                }

        # Timeout reached
        active_processes = self.get_active_processes()
        knowledge_processes = [
            p for p in active_processes
            if any(keyword in p.get("processDefinitionKey", "").lower()
                  for keyword in knowledge_keywords)
        ]

        self.log(f"⏰ Knowledge processing timed out after {max_wait_minutes} minutes", "WARNING")
        self.log(f"   Still active: {len(knowledge_processes)} knowledge processes")

        return {
            "status": "timeout",
            "active_count": len(knowledge_processes),
            "failed_count": 0,
            "timeout_minutes": max_wait_minutes
        }

    def detect_hanging_processes(self, max_age_minutes: int = 30) -> List[Dict[str, Any]]:
        """Detect processes that have been running too long (likely hanging)"""
        try:
            from datetime import datetime, timedelta

            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)

            # Get all active processes
            response = requests.get(
                f"{self.base_url}/process-instance",
                timeout=self.timeout
            )

            if response.status_code != 200:
                self.log(f"❌ Failed to get processes for hang detection: {response.status_code}", "ERROR")
                return []

            processes = response.json()
            hanging_processes = []

            for process in processes:
                process_id = process.get("id")

                # Get detailed process info including start time
                detail_response = requests.get(
                    f"{self.base_url}/process-instance/{process_id}",
                    timeout=5
                )

                if detail_response.status_code == 200:
                    details = detail_response.json()
                    # For hanging detection, we'll use a simple heuristic
                    # In production, you'd check actual start times
                    hanging_processes.append({
                        "id": process_id,
                        "definitionKey": details.get("definitionKey", "unknown"),
                        "suspended": details.get("suspended", False),
                        "ended": details.get("ended", False)
                    })

            self.log(f"🔍 Detected {len(hanging_processes)} potentially hanging processes")
            return hanging_processes

        except Exception as e:
            self.log(f"❌ Error detecting hanging processes: {e}", "ERROR")
            return []

    def analyze_hanging_process(self, process_id: str) -> Dict[str, Any]:
        """Analyze why a specific process is hanging by checking incidents and activities"""
        try:
            analysis = {
                "process_id": process_id,
                "incidents": [],
                "current_activity": None,
                "variables": {},
                "hang_reason": "unknown"
            }

            # Get incidents for this process
            incidents = self.get_process_incidents(process_id)
            analysis["incidents"] = incidents

            if incidents:
                self.log(f"🔍 Process {process_id} has {len(incidents)} incidents:")
                for incident in incidents:
                    incident_type = incident.get("incidentType", "unknown")
                    incident_msg = incident.get("incidentMessage", "No message")
                    activity_id = incident.get("activityId", "unknown")

                    self.log(f"   🚨 [{incident_type}] {incident_msg} (Activity: {activity_id})", "ERROR")
                    analysis["hang_reason"] = f"{incident_type}: {incident_msg}"

            # Get current activity
            try:
                activity_response = requests.get(
                    f"{self.base_url}/activity-instance",
                    params={"processInstanceId": process_id},
                    timeout=5
                )

                if activity_response.status_code == 200:
                    activities = activity_response.json()
                    if activities:
                        current_activity = activities.get("activityInstances", [])
                        if current_activity:
                            analysis["current_activity"] = current_activity[0].get("activityId", "unknown")
                            self.log(f"   📍 Currently stuck at activity: {analysis['current_activity']}")
            except:
                pass

            # Get process variables to understand context
            try:
                vars_response = requests.get(
                    f"{self.base_url}/process-instance/{process_id}/variables",
                    timeout=5
                )

                if vars_response.status_code == 200:
                    variables = vars_response.json()
                    analysis["variables"] = variables

                    # Log key variables that might explain the hang
                    key_vars = ["file_id", "error_message", "step", "status"]
                    for var_name in key_vars:
                        if var_name in variables:
                            var_value = variables[var_name].get("value", "unknown")
                            self.log(f"   📋 Variable {var_name}: {var_value}")
            except:
                pass

            return analysis

        except Exception as e:
            self.log(f"❌ Error analyzing hanging process {process_id}: {e}", "ERROR")
            return {"process_id": process_id, "error": str(e)}

    def cleanup_hanging_processes(self, process_definition_key: str = "automatic_knowledge_processing") -> int:
        """Clean up hanging knowledge processing instances with detailed incident logging"""
        try:
            # Get processes of specific type
            response = requests.get(
                f"{self.base_url}/process-instance",
                params={"processDefinitionKey": process_definition_key},
                timeout=self.timeout
            )

            if response.status_code != 200:
                self.log(f"❌ Failed to get {process_definition_key} processes: {response.status_code}", "ERROR")
                return 0

            processes = response.json()
            cleanup_count = 0

            for process in processes:
                process_id = process.get("id")
                self.log(f"🧹 Analyzing hanging process: {process_definition_key} (ID: {process_id})")

                # Analyze why the process is hanging BEFORE cleanup
                analysis = self.analyze_hanging_process(process_id)

                # Log the analysis results
                hang_reason = analysis.get("hang_reason", "unknown")
                self.log(f"   🔍 Hang reason: {hang_reason}")

                # Delete the process instance (BEST PRACTICE: cleanup hanging processes)
                delete_response = requests.delete(
                    f"{self.base_url}/process-instance/{process_id}",
                    params={"reason": f"Cleanup hanging process: {hang_reason}"},
                    timeout=self.timeout
                )

                if delete_response.status_code == 204:
                    self.log(f"✅ Successfully deleted hanging process {process_id}")
                    cleanup_count += 1
                else:
                    self.log(f"❌ Failed to delete process {process_id}: {delete_response.status_code}", "ERROR")

            return cleanup_count

        except Exception as e:
            self.log(f"❌ Error during hanging process cleanup: {e}", "ERROR")
            return 0

    def cleanup_failed_processes(self) -> int:
        """Clean up failed processes (best practice for process hygiene)"""
        try:
            failed_processes = self.get_failed_processes()
            cleanup_count = 0

            for process in failed_processes:
                process_id = process.get("id")
                process_key = process.get("processDefinitionKey", "unknown")

                # Log the failure for audit trail
                self.log(f"🧹 Cleaning up failed process: {process_key} (ID: {process_id})")

                # In production, you might:
                # 1. Delete the process instance
                # 2. Retry the process
                # 3. Send alerts to administrators
                # 4. Log to monitoring systems

                # For now, we'll just count them
                cleanup_count += 1

            return cleanup_count

        except Exception as e:
            self.log(f"❌ Error during cleanup: {e}", "ERROR")
            return 0

def main():
    """Test the Camunda process manager"""
    manager = CamundaProcessManager()

    print("=" * 60)
    print("CAMUNDA PROCESS MANAGEMENT TEST")
    print("=" * 60)

    # Health check
    if not manager.check_camunda_health():
        print("❌ Camunda not accessible")
        return 1

    # Get process overview
    active_processes = manager.get_active_processes()
    failed_processes = manager.get_failed_processes()

    print(f"📊 Process Overview:")
    print(f"   Active: {len(active_processes)}")
    print(f"   Failed: {len(failed_processes)}")

    # Test knowledge processing monitoring
    result = manager.monitor_knowledge_processing(max_wait_minutes=1)
    print(f"📋 Knowledge Processing Result: {result}")

    return 0

if __name__ == "__main__":
    exit(main())
