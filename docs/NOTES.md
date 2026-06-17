## Main Objective

This project is not intended to replace native tools engineered by far more experienced professionals. It is a study project and, at the same time, a practical implementation of a custom vision regarding the best approach for specific processing tasks. For critical everyday use and rock-solid reliability, native tools remain the standard choice. However, if you wish to support the project by contributing feedback or want to experiment with a fresh workflow, you are very welcome.


## The Approach

My vision is straightforward: while tools like `subprocess` excel in performance and handle a massive array of edge cases, they tend to be highly separatist when dealing with different operating systems. Consequently, operations that should be simple, humanly readable, and maintainable often become unnecessarily complex. 

My goal is to delegate clear boundaries to each architectural responsibility: Executions, Tasks, and Results—each has its dedicated place. Executing `subprocess.run` with dozens of inline parameters might seem direct, but it quickly becomes exhausting to scale and maintain. This framework focuses on a clean division of concerns. Furthermore, the objective is to ensure that identical functionalities operate exactly the same way across POSIX and Windows NT environments. The underlying `pipe`, `close`, and `waitpid` interfaces must accept the same parameters and execute uniformly, regardless of the host platform.


## Challenges and Plans

The plan is simple: I don't want to reinvent the wheel; I want to improve its design for specific modern demands. With the rapid expansion of AI orchestration, CLI agents routinely issue system commands, often relying on cheap, low-abstraction execution layers and unstable sync/async logic. 

By contrast, our `Task` object statefully stores both the input and output stream buffers alongside the command payload itself, allowing it to be reused, passed around, and enhanced over time. This approach prevents writing redundant command sequences and keeps data localized. 

Naturally, this architecture introduces the massive barrier of POSIX and NT cross-compatibility. The Python community has done a magnificent job creating brilliant standard libraries, but high-level tools frequently diverge. A clear example of this fragmentation is seen in the ecosystem split between `uv`, `pipx`, `pip`, and `poetry`—essentially the same core functional goals driven by different logic, visions, and compatibility constraints. This project focuses on mitigating that exact lack of compatibility at the lowest process-spawning layer.


## Final Considerations

With the overwhelming market demand for web frameworks and AI products, the industry often overlooks the foundational low-level tools that make these technologies possible in the first place. I remember when `subprocess` was barely in its infancy and we had to rely on `os.system`, redirecting raw stdout to temporary files via `echo` just to retrieve data later. 

Things must evolve. That is why every idea, no matter how unconventional it seems, should be explored and shared. A single piece of feedback or constructive criticism can pivot an entire architecture. If you are reading this and find the premise interesting, your insights and contributions are highly appreciated.
