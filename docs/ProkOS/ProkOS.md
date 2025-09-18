ProkOS - A process centric operating system (Basic)<br>
<br>
At the heart of the system is a **microkernel**. Its job is not to do everything, but to make sure the core process engine is alive and ready. Concretely, the microkernel:<br>
<br>
1. **Bootstraps Camunda (the process engine stack).**<br>
   It ensures that Camunda is up and running, and pushes in the minimal “kernel-level” or “virtual OS-level” BPMN processes needed for the system to function.<br>
<br>
2. **Starts the Process Definition Orchestrator (PDO).**<br>
   The PDO is a special BPMN process that runs recursively. Think of it as a heartbeat: it loops continuously, monitoring Camunda for any active process definitions and the tasks they spawn. Because it is recursive, the PDO can call itself, enabling ongoing oversight without needing to be manually restarted.<br>
<br>
3. **Coordinates Task Definition Executors (TDEs).**<br>
   Whenever the PDO encounters an active task, it tags it to its parent process, and then hands it off to the appropriate TDE.<br>
<br>
   * A **TDE** is a process in its own right, but it operates at the “task granularity.”<br>
   * Each TDE runs with a simple structure: **Input → Execute → Output.**<br>
   * There can be many types of TDEs (e.g., one that runs Python scripts, another that calls an external service, another that queries a database).<br>
<br>
Together, this creates a clean layering:<br>
<br>
* **Microkernel**: starts and sustains the environment (Camunda + core processes).<br>
* **PDO**: the recursive overseer, monitoring all process definitions and routing tasks.<br>
* **TDEs**: the workhorses that actually carry out the tasks, each encapsulated as its own small process.<br>
<br>
This structure makes the system process-centric: everything is expressed and executed as BPMN, from the high-level orchestration down to the smallest script task. It also makes the system resilient, because the PDO never stops looping, and modular, because new types of TDEs can be introduced without touching the kernel.<br>
<br>
```mermaid<br>
flowchart TB<br>
  subgraph L0[Layer 0 • Microkernel]<br>
    MK[Microkernel<br> - Boot Camunda stack <br>- Load kernel BPMN]<br>
  end<br>
<br>
  subgraph L1[Layer 1 • Process State Engine]<br>
    CE[Camunda State Engine]<br>
    KP["Kernel BPMN Processes<br>(e.g., health checks, <br>registration, etc.)"]<br>
    CE --- KP<br>
  end<br>
<br>
  subgraph L2["Layer 2 • Process Definition Orchestrator (PDO)"]<br>
    direction TB<br>
    PDO["PDO (Recursive BPMN)"] -->|loop|PDO<br>
    PDO -->|scan| Q[(Active Process/Tasks)] --> CE<br>
     PDO -->|dispatch|ROUTE["LLM - Task Router<br>(tag process+task)"]<br>
  end<br>
<br>
  subgraph L3["Layer 3 • Task Definition Executors (TDEs)"]<br>
    direction LR<br>
    TDE1["TDE • Script Runner<br>(Input→Execute→Output)"]<br>
    TDE2["TDE • External Service Caller<br>(Input→Execute→Output)"]<br>
    TDE3["TDE • Data/DB Worker<br>(Input→Execute→Output)"]<br>
  end<br>
<br>
  subgraph EXT[External Systems]<br>
    SVC1[HTTP/GRPC Services]<br>
    DB[(Datastores)]<br>
    TOOLS[Tools / Runtimes]<br>
  end<br>
<br>
  %% vertical layering<br>
  MK --> CE<br>
  CE --> PDO<br>
  ROUTE --> TDE1<br>
  ROUTE --> TDE2<br>
  ROUTE --> TDE3<br>
<br>
  %% IO edges<br>
  TDE1 -->|results| CE<br>
  TDE2 -->|results| CE<br>
  TDE3 -->|results| CE<br>
<br>
  %% External interactions<br>
  TDE2 --- SVC1<br>
  TDE3 --- DB<br>
  TDE1 --- TOOLS<br>
```<br>

