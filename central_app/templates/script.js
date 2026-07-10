document.addEventListener("DOMContentLoaded", function () {
        var showAgents = document.getElementById("show-agents");
        if (showAgents) {
          showAgents.addEventListener("click", function (e) {
            e.preventDefault();
            var agentsTable = document.getElementById("agents-table");
            if (agentsTable) {
              agentsTable.style.display = "block";
              document.getElementById("main-content").innerHTML =
                agentsTable.outerHTML;
            }
          });
        }

        // Initialize intelligence form
        initializeIntelligenceForm();

        // Fetch agents on page load
        fetchAgents();
      });

      function initializeIntelligenceForm() {
        var openIntelligenceBtn = document.getElementById(
          "open-add-intelligence",
        );
        var closeSidebarBtn = document.getElementById("close-sidebar");
        var submitBtn = document.getElementById("submit-intelligence");

        if (openIntelligenceBtn) {
          openIntelligenceBtn.addEventListener("click", function () {
            openAddIntelligenceSidebar();
          });
        }

        if (closeSidebarBtn) {
          closeSidebarBtn.addEventListener("click", function () {
            closeAddIntelligenceSidebar();
          });
        }

        if (submitBtn) {
          submitBtn.addEventListener("click", function () {
            submitIntelligenceForm();
          });
        }
      }

      function openAddIntelligenceSidebar() {
        var sidebar = document.getElementById("add-intelligence-sidebar");
        if (sidebar) {
          sidebar.classList.add("open");
        }
      }

      function closeAddIntelligenceSidebar() {
        var sidebar = document.getElementById("add-intelligence-sidebar");
        if (sidebar) {
          sidebar.classList.remove("open");
        }
      }

      var intelligenceSubmitInFlight = false;

      function parseErrorMessage(raw) {
        if (!raw) {
          return "Upload failed";
        }
        if (typeof raw === "object") {
          return raw.message || raw.error || JSON.stringify(raw);
        }
        var text = String(raw).trim();
        if (text.charAt(0) === "{") {
          try {
            var parsed = JSON.parse(text);
            return parsed.message || parsed.error || text;
          } catch (e) {
            return text;
          }
        }
        return text;
      }

      function showNotification(message, type, duration) {
        document.querySelectorAll(".notification").forEach((n) => n.remove());

        var notification = document.createElement("div");
        notification.className = "notification " + type;
        notification.textContent = message;

        document.body.appendChild(notification);

        if (duration) {
          setTimeout(function () {
            notification.remove();
          }, duration);
        }
      }

      function validateFileAgainstEngine(fileName, engine) {
        if (!fileName.includes(".")) {
          return false;
        }
        const extension = fileName.split(".").pop().toLowerCase();

        const engineMapping = {
          python: ["py"],
          node: ["js"],
          java: ["java"],
        };

        return engineMapping[engine]?.includes(extension);
      }

      function setSubmittingState(isSubmitting) {
        intelligenceSubmitInFlight = isSubmitting;
        var submitBtn = document.getElementById("submit-intelligence");
        if (!submitBtn) {
          return;
        }
        submitBtn.disabled = isSubmitting;
        submitBtn.textContent = isSubmitting ? "Uploading..." : "Submit";
      }

      function fetchAgents() {
        fetch("/get-agents")
          .then((response) => response.json())
          .then((data) => {
            const agentSelect = document.getElementById("agent-select");
            if (!agentSelect) return;

            agentSelect.innerHTML =
              '<option value="">-- Select an Agent --</option>';
            if (Array.isArray(data) && data.length > 0) {
              data.forEach((agent) => {
                const option = document.createElement("option");
                option.value = agent.name;
                option.textContent = agent.name;
                agentSelect.appendChild(option);
              });
            }
          })
          .catch((error) => {
            console.error("Error fetching agents:", error);
            showNotification("Error loading agents", "error");
          });
      }

      function submitIntelligenceForm() {
        if (intelligenceSubmitInFlight) {
          showNotification(
            "Upload already in progress. Please wait...",
            "info",
            3000,
          );
          return;
        }

        const intelligenceName = document
          .getElementById("intelligence-name")
          .value.trim();
        const description = document.getElementById("description").value.trim();
        const engine = document.getElementById("engine-select").value;
        const version = document.getElementById("engine-version").value.trim();
        const fileInput = document.getElementById("code-file");
        const agent = document.getElementById("agent-select").value;

        if (
          !intelligenceName ||
          !description ||
          !engine ||
          !version ||
          !agent ||
          !fileInput.files.length
        ) {
          showNotification(
            "Please fill in all fields and select a file",
            "error",
          );
          return;
        }

        const fileName = fileInput.files[0].name;

        if (!validateFileAgainstEngine(fileName, engine)) {
          showNotification(
            `Selected file does not match ${engine} runtime engine`,
            "error",
          );
          return;
        }

        setSubmittingState(true);
        showNotification("Creating intelligence...", "info", 5000);

        const formData = new FormData();
        formData.append("intelligence_name", intelligenceName);
        formData.append("description", description);
        formData.append("engine", engine);
        formData.append("version", version);
        formData.append("agent_name", agent);
        formData.append("file", fileInput.files[0]);

        fetch("/add-intelligence", {
          method: "POST",
          body: formData,
        })
          .then(async (response) => {
            let data = {};
            try {
              data = await response.json();
            } catch (e) {
              data = {};
            }

            if (!response.ok) {
              throw new Error(
                parseErrorMessage(
                  data.message || data.error || "Upload failed",
                ),
              );
            }

            return data;
          })
          .then((data) => {
            console.log("Upload response:", data);

            if (data.status === "success") {
              showNotification(
                data.message || "Intelligence created successfully!",
                "success",
                4000,
              );

              resetIntelligenceForm();

              setTimeout(function () {
                closeAddIntelligenceSidebar();
              }, 1500);
            } else {
              showNotification(
                parseErrorMessage(
                  data.message || data.error || "Error creating intelligence",
                ),
                "error",
                5000,
              );
            }
          })
          .catch((error) => {
            console.error("Error:", error);
            showNotification(parseErrorMessage(error.message), "error", 5000);
          })
          .finally(function () {
            setSubmittingState(false);
          });
      }

      function resetIntelligenceForm() {
        document.getElementById("intelligence-name").value = "";
        document.getElementById("description").value = "";
        document.getElementById("engine-select").value = "python";
        document.getElementById("engine-version").value = "";
        document.getElementById("code-file").value = "";
        document.getElementById("agent-select").value = "";
      }