async function apiRequest(url, options = {}) {
  const opts = {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
    ...options,
  };
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.error) msg = data.error;
    } catch { }
    throw new Error(msg);
  }
  try {
    return await res.json();
  } catch {
    return null;
  }
}

// Detect which page we are on
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  if (path.endsWith("/login-page") || path.endsWith("/login.html")) {
    initStudentLogin();
  } else if (path.endsWith("/register-page") || path.endsWith("/register.html")) {
    initStudentRegister();
  } else if (path.endsWith("/student-dashboard") || path.endsWith("/student_dashboard.html")) {
    initStudentDashboard();
  } else if (path.endsWith("/admin") || path.endsWith("/admin.html") || path.endsWith("/admin_dashboard.html")) {
    initAdminDashboard();
  }
});

function initStudentLogin() {
  const form = document.getElementById("login-form");
  const errorBox = document.getElementById("login-error");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.textContent = "";
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    try {
      const res = await apiRequest("/login", { method: "POST", body: payload });
      if (res.role === "student") {
        window.location.href = "/student-dashboard";
      } else {
        errorBox.textContent = "Unexpected role.";
      }
    } catch (err) {
      errorBox.textContent = err.message;
    }
  });
}

function initStudentRegister() {
  const form = document.getElementById("register-form");
  const errorBox = document.getElementById("register-error");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.textContent = "";
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    try {
      await apiRequest("/register", { method: "POST", body: payload });
      window.location.href = "/student-dashboard";
    } catch (err) {
      errorBox.textContent = err.message;
    }
  });
}

// Student dashboard
function initStudentDashboard() {
  wireSidebarNavigation();
  wireStudentActions();
  wireDashboardGoSchedule();
  wireStudentModal();
  renderStudentCourses();
  renderStudentSchedule();
}

function wireSidebarNavigation() {
  const navButtons = document.querySelectorAll(".sidebar-nav .nav-item");
  const sections = document.querySelectorAll(".content-section");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const target = btn.getAttribute("data-section");
      sections.forEach((sec) => {
        sec.classList.toggle("active", sec.id === target);
      });
    });
  });
}

function wireDashboardGoSchedule() {
  const link = document.getElementById("dashboard-go-schedule");
  if (link) {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const scheduleSection = document.getElementById("schedule-section");
      const navButtons = document.querySelectorAll(".sidebar-nav .nav-item");
      const sections = document.querySelectorAll(".content-section");
      navButtons.forEach((b) => b.classList.remove("active"));
      const scheduleBtn = document.querySelector('.nav-item[data-section="schedule-section"]');
      if (scheduleBtn) scheduleBtn.classList.add("active");
      sections.forEach((sec) => sec.classList.toggle("active", sec === scheduleSection));
    });
  }
}

function wireStudentActions() {
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await apiRequest("/logout", { method: "POST" });
      } finally {
        window.location.href = "/";
      }
    });
  }

  async function doGenerate(courseIds, courseSections) {
    try {
      if (courseSections && courseSections.length > 0) {
        await apiRequest("/generate-schedule", {
          method: "POST",
          body: { course_sections: courseSections },
        });
        await renderStudentSchedule();
        return;
      }
      if (!courseIds || !courseIds.length) {
        throw new Error("Select at least one course from the 'Available Courses' list.");
      }
      await apiRequest("/generate-schedule", {
        method: "POST",
        body: { course_ids: courseIds },
      });
      await renderStudentSchedule();
    } catch (err) {
      throw err;
    }
  }

  function getSelectedForGenerate() {
    const selected = Array.from(document.querySelectorAll("#courses-section [data-selected-course='true']"));
    const sections = selected.map((el) => el.dataset.courseSection).filter(Boolean);
    if (sections.length > 0) return { courseSections: sections };
    const ids = [...new Set(selected.map((el) => Number(el.dataset.courseId)))].filter(Boolean);
    return { courseIds: ids };
  }

  const generateBtn = document.getElementById("generate-schedule-btn");
  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      const sel = getSelectedForGenerate();
      try {
        generateBtn.disabled = true;
        generateBtn.textContent = "Generating...";
        await doGenerate(sel.courseIds, sel.courseSections);
        alert("Success! Your schedule has been updated.");
        const schedTabBtn = document.querySelector('[data-section="schedule-section"]');
        if (schedTabBtn) schedTabBtn.click();
      } catch (err) {
        showConflictModal(err.message);
      } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "Generate Schedule";
      }
    });
  }

  const generateBtn2 = document.getElementById("generate-schedule-btn-2");
  if (generateBtn2) {
    generateBtn2.addEventListener("click", async () => {
      const selected = Array.from(document.querySelectorAll("[data-selected-course='true']"));
      const courseSections = selected.map((el) => el.dataset.courseSection).filter(Boolean);
      const courseIds = courseSections.length === 0
        ? [...new Set(selected.map((el) => Number(el.dataset.courseId)))].filter(Boolean)
        : [];
      try {
        await doGenerate(courseIds, courseSections.length ? courseSections : undefined);
        alert("Success! Your schedule has been updated.");
        const schedTabBtn = document.querySelector('[data-section="schedule-section"]');
        if (schedTabBtn) schedTabBtn.click();
      } catch (err) {
        showConflictModal(err.message);
      }
    });
  }

  const regenerateBtn = document.getElementById("regenerate-schedule-btn");
  if (regenerateBtn) {
    regenerateBtn.addEventListener("click", async () => {
      try {
        const schedule = await apiRequest("/schedule");
        const bySection = schedule.some((e) => e.course_section != null);
        if (bySection) {
          const courseSections = [...new Set(schedule.map((e) => e.course_section).filter(Boolean))];
          if (!courseSections.length) {
            alert("No courses in your schedule. Select courses and Generate first.");
            return;
          }
          await apiRequest("/generate-schedule", { method: "POST", body: { course_sections: courseSections } });
        } else {
          const courseIds = [...new Set(schedule.map((e) => e.course_id).filter(Boolean))];
          if (!courseIds.length) {
            alert("No courses in your schedule. Select courses and Generate first.");
            return;
          }
          await apiRequest("/generate-schedule", { method: "POST", body: { course_ids: courseIds } });
        }
        await renderStudentSchedule();
        alert("Schedule regenerated.");
      } catch (err) {
        showConflictModal(err.message);
      }
    });
  }

  const exportPdfBtn = document.getElementById("export-pdf-btn");
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", () => {
      window.location.href = "/schedule/export/pdf";
    });
  }
  const exportExcelBtn = document.getElementById("export-excel-btn");
  if (exportExcelBtn) {
    exportExcelBtn.addEventListener("click", () => {
      window.location.href = "/schedule/export/excel";
    });
  }
  const refreshBtn = document.getElementById("refresh-schedule-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => renderStudentSchedule());
  }

  const clearBtn = document.getElementById("clear-schedule-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to clear your entire schedule?")) return;
      try {
        await apiRequest("/clear-schedule", { method: "POST" });
        await renderStudentSchedule();
        alert("Schedule cleared.");
      } catch (err) {
        alert(err.message);
      }
    });
  }

  const searchInput = document.getElementById("course-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase();
      const items = document.querySelectorAll("#courses-list .list-item");
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(term) ? "" : "none";
      });
    });
  }
}

async function renderStudentCourses() {
  const coursesContainer = document.getElementById("courses-list");
  const selectedContainer = document.getElementById("selected-courses-list");
  if (!coursesContainer || !selectedContainer) return;
  coursesContainer.textContent = "Loading courses...";
  try {
    const [courses, sections] = await Promise.all([
      apiRequest("/courses"),
      apiRequest("/sections"),
    ]);
    coursesContainer.textContent = "";
    // Group sections by course_id for easier rendering
    const sectionsByCourse = {};
    if (sections && sections.length) {
      sections.forEach((s) => {
        if (!sectionsByCourse[s.course_id]) sectionsByCourse[s.course_id] = [];
        sectionsByCourse[s.course_id].push(s);
      });
    }
    courses.forEach((c) => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.dataset.courseId = c.course_id != null ? c.course_id : "";
      item.dataset.courseName = c.course_name || "";
      const main = document.createElement("div");
      main.className = "list-item-main";
      const dept = c.department != null ? c.department : "";
      const cred = c.credits != null ? `${c.credits} credits` : "";
      main.innerHTML = `<strong>${escapeHtml(c.course_code || c.course_name)} – ${escapeHtml(c.course_name)}</strong><br/>${dept ? `<span class="badge">${escapeHtml(dept)}</span> • ` : ""}${escapeHtml(cred)}`;
      item.appendChild(main);

      const courseSections = sectionsByCourse[c.course_id];
      if (courseSections && courseSections.length) {
        const sel = document.createElement("select");
        sel.className = "course-section-select";
        courseSections.forEach((sec) => {
          const opt = document.createElement("option");
          opt.value = sec.section_id;
          const sched = (sec.schedules || []).map(s => `${s.day_of_week.substring(0, 3)} ${s.start_time}`).join(", ");
          opt.textContent = `Sec ${sec.section_name || '?'}: ${sched} (${sec.instructor})`;
          sel.appendChild(opt);
        });
        item.appendChild(sel);
        const btn = document.createElement("button");
        btn.textContent = "Select";
        btn.addEventListener("click", () => {
          const courseSection = sel.value;
          if (!courseSection) return;
          item.dataset.courseSection = courseSection;
          item.dataset.selectedCourse = "true";
          btn.textContent = "Selected";
          const clone = item.cloneNode(true);
          clone.dataset.selectedCourse = "true";
          clone.dataset.courseSection = courseSection;
          clone.querySelector("button").textContent = "Remove";
          clone.querySelector("button").addEventListener("click", () => {
            clone.remove();
            item.dataset.selectedCourse = "false";
            item.dataset.courseSection = "";
            btn.textContent = "Select";
          });
          const existing = selectedContainer.querySelector(`[data-course-section="${courseSection}"]`);
          if (existing) existing.remove();
          selectedContainer.appendChild(clone);
        });
        item.appendChild(btn);
      } else {
        const btn = document.createElement("button");
        btn.textContent = "Select";
        btn.addEventListener("click", () => toggleCourseSelection(item, selectedContainer));
        item.appendChild(btn);
      }
      coursesContainer.appendChild(item);
    });
  } catch (err) {
    coursesContainer.textContent = err.message;
  }
}

function toggleCourseSelection(item, selectedContainer) {
  const alreadySelected = item.dataset.selectedCourse === "true";
  if (alreadySelected) {
    item.dataset.selectedCourse = "false";
    item.querySelector("button").textContent = "Select";
    const selectedItem = selectedContainer.querySelector(
      `[data-course-id="${item.dataset.courseId}"]`
    );
    if (selectedItem) selectedItem.remove();
  } else {
    item.dataset.selectedCourse = "true";
    item.querySelector("button").textContent = "Selected";
    const clone = item.cloneNode(true);
    clone.dataset.selectedCourse = "true";
    selectedContainer.appendChild(clone);
  }
}

async function renderStudentSchedule() {
  const timetableEl = document.getElementById("timetable");
  if (!timetableEl) return;
  timetableEl.textContent = "Loading schedule...";
  try {
    const data = await apiRequest("/schedule");
    timetableEl.textContent = "";
    renderTimetableGrid(timetableEl, data);
    updateDashboardCourseCount(data);
  } catch (err) {
    timetableEl.textContent = err.message;
  }
}

function updateDashboardCourseCount(entries) {
  const el = document.getElementById("dashboard-course-count");
  if (!el) return;
  const unique = new Set(entries.map((e) => (e.course_id != null ? e.course_id : e.course_code)));
  el.textContent = entries.length
    ? `${unique.size} course(s), ${entries.length} slot(s) in your schedule.`
    : "No courses scheduled. Go to Courses to select and generate.";
}

const DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const START_MINUTES = 8 * 60;
const END_MINUTES = 20 * 60;
const HOUR_HEIGHT = 48;
const MINUTES_RANGE = END_MINUTES - START_MINUTES;

function parseTime12(str) {
  const parts = (str || "").trim().split(/\s+/);
  const time = parts[0] || "";
  const ampm = (parts[1] || "").toUpperCase();
  let [h, m] = time.split(":").map((x) => parseInt(x, 10) || 0);
  if (ampm === "PM" && h !== 12) h += 12;
  if (ampm === "AM" && h === 12) h = 0;
  return h * 60 + m;
}

function parseTime24(str) {
  const [h, m] = (str || "").split(":").map((x) => parseInt(x, 10) || 0);
  return h * 60 + (m || 0);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
function renderTimetableGrid(container, entries) {
  const grid = document.createElement("div");
  grid.className = "timetable-grid";

  const corner = document.createElement("div");
  corner.className = "timetable-corner";
  corner.style.gridColumn = "1";
  corner.style.gridRow = "1";
  grid.appendChild(corner);

  DAYS.forEach((day, idx) => {
    const h = document.createElement("div");
    h.className = "timetable-header";
    h.textContent = day;
    h.style.gridColumn = String(idx + 2);
    h.style.gridRow = "1";
    grid.appendChild(h);
  });

  let row = 2;
  for (let minutes = START_MINUTES; minutes < END_MINUTES; minutes += 60) {
    const hourLabel = document.createElement("div");
    hourLabel.className = "timetable-timecell";
    hourLabel.style.gridColumn = "1";
    hourLabel.style.gridRow = String(row);
    const h12 = ((minutes / 60 + 11) % 12) + 1;
    const ampm = minutes / 60 >= 12 ? "PM" : "AM";
    hourLabel.textContent = `${String(h12).padStart(2, "0")}:00 ${ampm}`;
    grid.appendChild(hourLabel);
    for (let d = 0; d < 7; d++) {
      const cell = document.createElement("div");
      cell.className = "timetable-slot";
      cell.style.gridColumn = String(d + 2);
      cell.style.gridRow = String(row);
      grid.appendChild(cell);
    }
    row += 1;
  }

  DAYS.forEach((day, idx) => {
    const col = document.createElement("div");
    col.className = "timetable-day-column";
    col.dataset.day = day;
    col.style.gridColumn = String(idx + 2);
    col.style.gridRow = "2 / 14";
    col.style.position = "relative";
    grid.appendChild(col);
  });
  container.appendChild(grid);

  const dayColumns = {};
  grid.querySelectorAll(".timetable-day-column").forEach((col) => {
    dayColumns[col.dataset.day] = col;
  });
  const heightPx = HOUR_HEIGHT * 12;

  const colorMap = {};
  const baseColors = ["#3b82f6", "#8b5cf6", "#22c55e", "#f97316", "#ec4899"];
  let colorIndex = 0;

  const abbrMap = {
    "sat": "Saturday", "sun": "Sunday", "mon": "Monday",
    "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday"
  };

  entries.forEach((entry) => {
    const daysArr = (entry.day_of_week || "").split(",").map(d => d.trim().toLowerCase());

    daysArr.forEach(d => {
      const fullDay = abbrMap[d] || (d.charAt(0).toUpperCase() + d.slice(1));
      const dayCol = dayColumns[fullDay] || dayColumns[
        Object.keys(dayColumns).find(k => k.toLowerCase() === fullDay.toLowerCase())
      ];
      if (!dayCol) return;

      const startMin = parseTime12(entry.start_time);
      const endMin = parseTime12(entry.end_time);
      const top = ((startMin - START_MINUTES) / MINUTES_RANGE) * heightPx;
      const height = Math.max(((endMin - startMin) / MINUTES_RANGE) * heightPx, 32);

      if (!colorMap[entry.course_code]) {
        colorMap[entry.course_code] = baseColors[colorIndex % baseColors.length];
        colorIndex += 1;
      }
      const block = document.createElement("div");
      block.className = "timetable-event";
      block.style.top = `${top}px`;
      block.style.height = `${height}px`;
      block.style.background = colorMap[entry.course_code];
      block.dataset.sectionId = entry.section_id;
      block.dataset.enrollmentId = entry.enrollment_id;
      block.dataset.courseId = entry.course_id != null ? entry.course_id : "";
      block.dataset.day = entry.day_of_week;
      block.dataset.startMinutes = String(startMin);
      block.dataset.endMinutes = String(endMin);
      block.innerHTML = `
        <div class="event-title">${escapeHtml(entry.course_name)}</div>
        <div class="event-meta">${escapeHtml(entry.instructor || "")}</div>
        <div class="event-meta">${escapeHtml(entry.classroom || "")}</div>
        <div class="event-meta">${entry.start_time} – ${entry.end_time}</div>
        <div class="event-actions">

        <button type="button" data-action="delete" class="secondary">Remove</button>
      </div>
    `;

      block.addEventListener("click", () => {
        showEventDetail(entry);
      });

      attachEventActions(block);
      dayCol.appendChild(block);
    });
  });
}

function showEventDetail(entry) {
  const bodyHtml = `
    <div class="event-detail-card">
      <div class="modal-detail-row">
        <span class="modal-detail-label">Course Code</span>
        <span class="modal-detail-value">${escapeHtml(entry.course_code)}</span>
      </div>
      <div class="modal-detail-row">
        <span class="modal-detail-label">Course Name</span>
        <span class="modal-detail-value">${escapeHtml(entry.course_name)}</span>
      </div>
      <div class="modal-detail-row">
        <span class="modal-detail-label">Instructor</span>
        <span class="modal-detail-value">${escapeHtml(entry.instructor || "TBD")}</span>
      </div>
      <div class="modal-detail-row">
        <span class="modal-detail-label">Location</span>
        <span class="modal-detail-value">${escapeHtml(entry.classroom || "TBD")}</span>
      </div>
      <div class="modal-detail-row">
        <span class="modal-detail-label">Day</span>
        <span class="modal-detail-value">${escapeHtml(entry.day_of_week)}</span>
      </div>
      <div class="modal-detail-row">
        <span class="modal-detail-label">Time</span>
        <span class="modal-detail-value">${entry.start_time} – ${entry.end_time}</span>
      </div>
      ${entry.section_name ? `
      <div class="modal-detail-row">
        <span class="modal-detail-label">Section</span>
        <span class="modal-detail-value">${escapeHtml(entry.section_name)}</span>
      </div>` : ""}
    </div>
  `;
  studentShowModal(entry.course_name, bodyHtml);
}

function studentShowModal(title, bodyHtml) {
  const overlay = document.getElementById("student-modal-overlay");
  const titleEl = document.getElementById("student-modal-title");
  const bodyEl = document.getElementById("student-modal-body");
  if (overlay && titleEl && bodyEl) {
    titleEl.textContent = title;
    bodyEl.innerHTML = bodyHtml;
    overlay.classList.remove("hidden");
  }
}

function studentCloseModal() {
  const overlay = document.getElementById("student-modal-overlay");
  if (overlay) overlay.classList.add("hidden");
}

function showConflictModal(message) {
  const bodyHtml = `
    <div style="text-align: center; padding: 1rem;">
      <div style="color: var(--error); font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
      <p style="margin-bottom: 1.5rem; line-height: 1.6;">${escapeHtml(message)}</p>
      <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 12px; font-size: 0.9rem; color: var(--text-muted); text-align: left;">
        <strong>How to Resolve:</strong>
        <ul style="margin-top: 0.5rem; padding-left: 1.2rem;">
          <li>Remove one of the conflicting courses from your selection.</li>
          <li>Choose a different section for one of the courses.</li>
          <li>Try generating a schedule with a different combination of courses.</li>
        </ul>
      </div>
      <button class="primary" style="margin-top: 2rem; width: 100%;" onclick="studentCloseModal()">Understood</button>
    </div>
  `;
  studentShowModal("Scheduling Conflict", bodyHtml);
}

function wireStudentModal() {
  const closeBtn = document.getElementById("student-modal-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", studentCloseModal);
  }
  const overlay = document.getElementById("student-modal-overlay");
  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) studentCloseModal();
    });
  }
}

function attachEventActions(block) {
  const deleteBtn = block.querySelector('button[data-action="delete"]');
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const enrollmentId = Number(block.dataset.enrollmentId);
      try {
        await apiRequest("/edit-schedule", {
          method: "POST",
          body: { action: "delete", enrollment_id: enrollmentId },
        });
        await renderStudentSchedule();
      } catch (err) {
        alert(err.message);
      }
    });
  }
}
// Admin side
function initAdminDashboard() {
  wireSidebarNavigation();
  wireAdminModal();
  wireAdminTableActions();
  wireAdminActions();
  wireAdminCourseUpload();
  loadAdminStatsAndTables();
}

function adminShowModal(title, bodyHtml) {
  const overlay = document.getElementById("admin-modal-overlay");
  const titleEl = document.getElementById("admin-modal-title");
  const bodyEl = document.getElementById("admin-modal-body");
  if (overlay && titleEl && bodyEl) {
    titleEl.textContent = title;
    bodyEl.innerHTML = bodyHtml;
    overlay.classList.remove("hidden");
  }
}

function adminCloseModal() {
  const overlay = document.getElementById("admin-modal-overlay");
  if (overlay) overlay.classList.add("hidden");
}

function wireAdminModal() {
  const closeBtn = document.getElementById("admin-modal-close");
  const overlay = document.getElementById("admin-modal-overlay");
  if (closeBtn) closeBtn.addEventListener("click", adminCloseModal);
  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) adminCloseModal();
    });
  }
}

function wireAdminCourseUpload() {
  const input = document.getElementById("admin-course-file-input");
  const btn = document.getElementById("admin-upload-course-btn");
  const status = document.getElementById("admin-upload-status");
  const fileNameEl = document.getElementById("admin-file-name");
  if (!btn || !input || !status) return;

  // Show selected filename
  input.addEventListener("change", () => {
    if (fileNameEl) {
      fileNameEl.textContent = input.files && input.files[0] ? input.files[0].name : "No file selected";
    }
  });

  btn.addEventListener("click", async () => {
    const file = input.files && input.files[0];
    if (!file) {
      status.innerHTML = "⚠️ Please select a file first.";
      status.className = "admin-upload-status error";
      return;
    }

    // Read selected mode
    const modeEl = document.querySelector('input[name="upload-mode"]:checked');
    const mode = modeEl ? modeEl.value : "append";

    if (mode === "replace" && !confirm("⚠️ Replace All will wipe ALL existing courses, sections and schedules before importing. Continue?")) {
      return;
    }

    btn.disabled = true;
    status.innerHTML = "⏳ Uploading and importing — please wait…";
    status.className = "admin-upload-status";

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("mode", mode);

      const res = await fetch("/admin/upload-course-file", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        status.innerHTML = `❌ ${data.error || `Upload failed (${res.status})`}`;
        status.className = "admin-upload-status error";
        return;
      }

      status.innerHTML = `
        ✅ <strong>Import successful!</strong><br>
        Rows processed: <strong>${data.rows_processed ?? "—"}</strong> &nbsp;|&nbsp;
        Courses: <strong>${data.courses ?? "—"}</strong> &nbsp;|&nbsp;
        Sections: <strong>${data.sections ?? "—"}</strong> &nbsp;|&nbsp;
        Schedules: <strong>${data.schedules ?? "—"}</strong>
      `;
      status.className = "admin-upload-status success";

      input.value = "";
      if (fileNameEl) fileNameEl.textContent = "No file selected";

      // Refresh stats & tables
      loadAdminStatsAndTables();

    } catch (err) {
      status.innerHTML = `❌ ${err.message || "Upload failed."}`;
      status.className = "admin-upload-status error";
    } finally {
      btn.disabled = false;
    }
  });
}


function wireAdminActions() {
  const logoutBtn = document.getElementById("admin-logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await apiRequest("/logout", { method: "POST" });
      } finally {
        window.location.href = "/";
      }
    });
  }
  const runConflictsBtn = document.getElementById("admin-run-conflicts-btn");
  if (runConflictsBtn) {
    runConflictsBtn.addEventListener("click", async () => {
      const roomList = document.getElementById("admin-room-conflicts");
      const instList = document.getElementById("admin-instructor-conflicts");
      roomList.textContent = "";
      instList.textContent = "";
      try {
        const res = await apiRequest("/admin/conflicts");
        res.room_conflicts.forEach((c) => {
          const li = document.createElement("li");
          li.textContent = `Schedules ${c.schedule_a} and ${c.schedule_b} in classroom ${c.classroom_id}`;
          roomList.appendChild(li);
        });
        res.instructor_conflicts.forEach((c) => {
          const li = document.createElement("li");
          li.textContent = `Schedules ${c.schedule_a} and ${c.schedule_b} for instructor ${c.instructor_id}`;
          instList.appendChild(li);
        });
        if (!roomList.children.length) {
          const li = document.createElement("li");
          li.textContent = "No room conflicts.";
          roomList.appendChild(li);
        }
        if (!instList.children.length) {
          const li = document.createElement("li");
          li.textContent = "No instructor conflicts.";
          instList.appendChild(li);
        }
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // Add Course
  const addCourseBtn = document.getElementById("admin-add-course-btn");
  if (addCourseBtn) {
    addCourseBtn.addEventListener("click", () => {
      const body = `
        <form id="admin-course-form">
          <div class="form-group">
            <label for="course-code">Code</label>
            <input type="text" id="course-code" name="course_code" placeholder="e.g. CS101" required />
          </div>
          <div class="form-group">
            <label for="course-name">Name</label>
            <input type="text" id="course-name" name="course_name" placeholder="e.g. Intro to Computer Science" required />
          </div>
          <div class="form-group">
            <label for="course-credits">Credits</label>
            <input type="number" id="course-credits" name="credits" value="3" min="1" />
          </div>
          <div class="form-group">
            <label for="course-dept">Department</label>
            <input type="text" id="course-dept" name="department" value="General" />
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Create Course</button>
          </div>
        </form>`;
      adminShowModal("Add Course", body);
      document.querySelector("[data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-course-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        try {
          await apiRequest("/admin/create-course", {
            method: "POST",
            body: {
              course_code: fd.get("course_code"),
              course_name: fd.get("course_name"),
              credits: parseInt(fd.get("credits"), 10) || 3,
              department: fd.get("department") || "General",
            },
          });
          adminCloseModal();
          loadAdminStatsAndTables();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  }

  // Add Section
  const addSectionBtn = document.getElementById("admin-add-section-btn");
  if (addSectionBtn) {
    addSectionBtn.addEventListener("click", async () => {
      let courses = [], instructors = [];
      try {
        [courses, instructors] = await Promise.all([
          apiRequest("/admin/courses"),
          apiRequest("/admin/instructors"),
        ]);
      } catch (err) {
        alert(err.message);
        return;
      }
      const courseOpts = courses.map((c) => `<option value="${c.course_id}">${c.course_code} – ${c.course_name}</option>`).join("");
      const instOpts = "<option value=''>— No instructor —</option>" + instructors.map((i) => `<option value="${i.instructor_id}">${i.name}</option>`).join("");
      const body = `
        <form id="admin-section-form">
          <div class="form-group">
            <label for="sec-course">Course</label>
            <select id="sec-course" name="course_id" required>${courseOpts}</select>
          </div>
          <div class="form-group">
            <label for="sec-inst">Instructor</label>
            <select id="sec-inst" name="instructor_id">${instOpts}</select>
          </div>
          <div class="form-group">
            <label for="sec-sem">Semester</label>
            <input type="text" id="sec-sem" name="semester" value="Spring 2026" />
          </div>
          <div class="form-group">
            <label for="sec-name">Section Name</label>
            <input type="text" id="sec-name" name="section_name" value="A" />
          </div>
          <div class="form-group">
            <label for="sec-day">Day of Week</label>
            <select id="sec-day" name="day_of_week" required>
              <option value="Monday">Monday</option>
              <option value="Tuesday">Tuesday</option>
              <option value="Wednesday">Wednesday</option>
              <option value="Thursday">Thursday</option>
              <option value="Friday">Friday</option>
              <option value="Saturday">Saturday</option>
              <option value="Sunday">Sunday</option>
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div class="form-group">
              <label for="sec-start">Start Time</label>
              <input type="time" id="sec-start" name="start_time" required />
            </div>
            <div class="form-group">
              <label for="sec-end">End Time</label>
              <input type="time" id="sec-end" name="end_time" required />
            </div>
          </div>
          <div class="form-group">
            <label for="sec-room">Classroom</label>
            <input type="text" id="sec-room" name="classroom" placeholder="e.g. Room 101" />
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Create Section</button>
          </div>
        </form>`;
      adminShowModal("Add Section", body);
      document.querySelector("[data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-section-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const instVal = fd.get("instructor_id");
        try {
          await apiRequest("/admin/create-section", {
            method: "POST",
            body: {
              course_id: parseInt(fd.get("course_id"), 10),
              instructor_id: instVal ? parseInt(instVal, 10) : null,
              semester: fd.get("semester") || "TBD",
              section_name: fd.get("section_name") || "A",
              day_of_week: fd.get("day_of_week"),
              start_time: fd.get("start_time"),
              end_time: fd.get("end_time"),
              classroom: fd.get("classroom") || "",
            },
          });
          adminCloseModal();
          loadAdminStatsAndTables();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  }
}

function escapeHtmlAdmin(str) {
  if (str == null) return "";
  const s = String(str);
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function wireAdminTableActions() {
  const main = document.querySelector(".main-content");
  if (!main) return;
  main.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-action");
    if (action === "edit-student") {
      const studentId = btn.getAttribute("data-student-id");
      const name = btn.getAttribute("data-name") || "";
      const email = btn.getAttribute("data-email") || "";
      const majorId = btn.getAttribute("data-major-id") || "";
      const year = btn.getAttribute("data-year") || "";
      const body = `
        <form id="admin-edit-student-form">
          <input type="hidden" name="student_id" value="${escapeHtmlAdmin(studentId)}" />
          <div class="form-group">
            <label for="edit-st-name">Name</label>
            <input type="text" id="edit-st-name" name="name" value="${escapeHtmlAdmin(name)}" required />
          </div>
          <div class="form-group">
            <label for="edit-st-email">Email</label>
            <input type="email" id="edit-st-email" name="email" value="${escapeHtmlAdmin(email)}" required />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div class="form-group">
              <label for="edit-st-major">Major ID</label>
              <input type="text" id="edit-st-major" name="major_id" value="${escapeHtmlAdmin(majorId)}" />
            </div>
            <div class="form-group">
              <label for="edit-st-year">Year</label>
              <input type="text" id="edit-st-year" name="year" value="${escapeHtmlAdmin(year)}" />
            </div>
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Save Changes</button>
          </div>
        </form>`;
      adminShowModal("Edit Student", body);
      document.querySelector("#admin-modal-body [data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-edit-student-form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        try {
          await apiRequest("/admin/update-student", {
            method: "PUT",
            body: {
              student_id: parseInt(fd.get("student_id"), 10),
              name: fd.get("name"),
              email: fd.get("email"),
              major_id: fd.get("major_id") || null,
              year: fd.get("year") || null,
            },
          });
          adminCloseModal();
          loadAdminStatsAndTables();
        } catch (err) {
          alert(err.message);
        }
      });
    } else if (action === "toggle-active") {
      const studentId = btn.getAttribute("data-student-id");
      const active = btn.getAttribute("data-active") === "true";
      try {
        await apiRequest("/admin/update-student", {
          method: "PUT",
          body: { student_id: parseInt(studentId, 10), is_active: !active },
        });
        loadAdminStatsAndTables();
      } catch (err) {
        alert(err.message);
      }
    } else if (action === "reset-password") {
      const studentId = btn.getAttribute("data-student-id");
      const body = `
        <form id="admin-reset-password-form">
          <input type="hidden" name="student_id" value="${escapeHtmlAdmin(studentId)}" />
          <div class="form-group">
            <label for="reset-pw">New Password</label>
            <input type="password" id="reset-pw" name="new_password" placeholder="••••••••" required />
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Reset Password</button>
          </div>
        </form>`;
      adminShowModal("Reset Password", body);
      document.querySelector("#admin-modal-body [data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-reset-password-form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        try {
          await apiRequest("/admin/reset-student-password", {
            method: "POST",
            body: {
              student_id: parseInt(fd.get("student_id"), 10),
              new_password: fd.get("new_password"),
            },
          });
          adminCloseModal();
          alert("Password reset.");
        } catch (err) {
          alert(err.message);
        }
      });
    } else if (action === "edit-course") {
      const cid = btn.getAttribute("data-course-id");
      const code = btn.getAttribute("data-code") || "";
      const name = btn.getAttribute("data-name") || "";
      const credits = btn.getAttribute("data-credits") || "3";
      const dept = btn.getAttribute("data-department") || "";
      const body = `
        <form id="admin-edit-course-form">
          <input type="hidden" name="course_id" value="${escapeHtmlAdmin(cid)}" />
          <div class="form-group">
            <label for="edit-c-code">Code</label>
            <input type="text" id="edit-c-code" name="course_code" value="${escapeHtmlAdmin(code)}" required />
          </div>
          <div class="form-group">
            <label for="edit-c-name">Name</label>
            <input type="text" id="edit-c-name" name="course_name" value="${escapeHtmlAdmin(name)}" required />
          </div>
          <div class="form-group">
            <label for="edit-c-credits">Credits</label>
            <input type="number" id="edit-c-credits" name="credits" value="${escapeHtmlAdmin(credits)}" min="1" />
          </div>
          <div class="form-group">
            <label for="edit-c-dept">Department</label>
            <input type="text" id="edit-c-dept" name="department" value="${escapeHtmlAdmin(dept)}" />
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Save Changes</button>
          </div>
        </form>`;
      adminShowModal("Edit Course", body);
      document.querySelector("#admin-modal-body [data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-edit-course-form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        try {
          await apiRequest("/admin/update-course", {
            method: "PUT",
            body: {
              course_id: parseInt(fd.get("course_id"), 10),
              course_code: fd.get("course_code"),
              course_name: fd.get("course_name"),
              credits: parseInt(fd.get("credits"), 10) || 3,
              department: fd.get("department") || "General",
            },
          });
          adminCloseModal();
          loadAdminStatsAndTables();
        } catch (err) {
          alert(err.message);
        }
      });
    } else if (action === "delete-course") {
      const courseId = btn.getAttribute("data-course-id");
      if (!confirm("Delete this course?")) return;
      try {
        await apiRequest(`/admin/delete-course?course_id=${courseId}`, { method: "DELETE" });
        loadAdminStatsAndTables();
      } catch (err) {
        alert(err.message);
      }
    } else if (action === "edit-section") {
      const sectionId = btn.getAttribute("data-section-id");
      const courseId = btn.getAttribute("data-course-id");
      const instructorId = btn.getAttribute("data-instructor-id") || "";
      const semester = btn.getAttribute("data-semester") || "TBD";
      let courses = [], instructors = [];
      try {
        [courses, instructors] = await Promise.all([
          apiRequest("/admin/courses"),
          apiRequest("/admin/instructors"),
        ]);
      } catch (err) {
        alert(err.message);
        return;
      }
      const courseOpts = courses.map((c) => `<option value="${c.course_id}" ${c.course_id === parseInt(courseId, 10) ? "selected" : ""}>${escapeHtmlAdmin(c.course_code)} – ${escapeHtmlAdmin(c.course_name)}</option>`).join("");
      const instOpts = "<option value=''>— No instructor —</option>" + instructors.map((i) => `<option value="${i.instructor_id}" ${i.instructor_id === parseInt(instructorId, 10) ? "selected" : ""}>${escapeHtmlAdmin(i.name)}</option>`).join("");
      const body = `
        <form id="admin-edit-section-form">
          <input type="hidden" name="section_id" value="${escapeHtmlAdmin(sectionId)}" />
          <div class="form-group">
            <label for="edit-sec-course">Course</label>
            <select id="edit-sec-course" name="course_id" required>${courseOpts}</select>
          </div>
          <div class="form-group">
            <label for="edit-sec-inst">Instructor</label>
            <select id="edit-sec-inst" name="instructor_id">${instOpts}</select>
          </div>
          <div class="form-group">
            <label for="edit-sec-sem">Semester</label>
            <input type="text" id="edit-sec-sem" name="semester" value="${escapeHtmlAdmin(semester)}" />
          </div>
          <div class="modal-actions" style="display: flex; gap: 1rem; margin-top: 2rem;">
            <button type="button" class="secondary" data-modal-cancel style="flex: 1;">Cancel</button>
            <button type="submit" class="primary" style="flex: 1;">Save Changes</button>
          </div>
        </form>`;
      adminShowModal("Edit Section", body);
      document.querySelector("#admin-modal-body [data-modal-cancel]").addEventListener("click", adminCloseModal);
      document.getElementById("admin-edit-section-form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        const instVal = fd.get("instructor_id");
        try {
          await apiRequest("/admin/update-section", {
            method: "PUT",
            body: {
              section_id: parseInt(fd.get("section_id"), 10),
              course_id: parseInt(fd.get("course_id"), 10),
              instructor_id: instVal ? parseInt(instVal, 10) : null,
              semester: fd.get("semester") || "TBD",
            },
          });
          adminCloseModal();
          loadAdminStatsAndTables();
        } catch (err) {
          alert(err.message);
        }
      });
    } else if (action === "delete-section") {
      const sectionId = btn.getAttribute("data-section-id");
      if (!confirm("Delete this section?")) return;
      try {
        await apiRequest(`/admin/delete-section?section_id=${sectionId}`, { method: "DELETE" });
        loadAdminStatsAndTables();
      } catch (err) {
        alert(err.message);
      }
    }
  });
}

async function loadAdminStatsAndTables() {
  try {
    const stats = await apiRequest("/admin/stats");
    document.getElementById("stat-total-students").textContent = stats.total_students;
    document.getElementById("stat-total-courses").textContent = stats.total_courses;
    document.getElementById("stat-total-sections").textContent = stats.total_sections;
    document.getElementById("stat-total-instructors").textContent = stats.total_instructors;
    document.getElementById("stat-total-classrooms").textContent = stats.total_classrooms;
  } catch { }
  const studentsTbody = document.querySelector("#admin-students-table tbody");
  if (studentsTbody) studentsTbody.innerHTML = "";
  try {
    const students = await apiRequest("/admin/students");
    students.forEach((s) => {
      const tr = document.createElement("tr");
      const act = s.is_active ? "Deactivate" : "Activate";
      tr.innerHTML = `
        <td>${escapeHtmlAdmin(s.student_id)}</td>
        <td>${escapeHtmlAdmin(s.name)}</td>
        <td>${escapeHtmlAdmin(s.email)}</td>
        <td>${escapeHtmlAdmin(s.major_id)}</td>
        <td>${escapeHtmlAdmin(s.year)}</td>
        <td>${s.is_active ? "Yes" : "No"}</td>
        <td>
          <button type="button" class="secondary small" data-action="edit-student" data-student-id="${s.student_id}" data-name="${escapeHtmlAdmin(s.name)}" data-email="${escapeHtmlAdmin(s.email)}" data-major-id="${escapeHtmlAdmin(s.major_id)}" data-year="${escapeHtmlAdmin(s.year)}">Edit</button>
          <button type="button" class="secondary small" data-action="toggle-active" data-student-id="${s.student_id}" data-active="${s.is_active}">${act}</button>
          <button type="button" class="secondary small" data-action="reset-password" data-student-id="${s.student_id}">Reset password</button>
        </td>`;
      studentsTbody.appendChild(tr);
    });
  } catch { }

  const coursesTbody = document.querySelector("#admin-courses-table tbody");
  if (coursesTbody) coursesTbody.innerHTML = "";
  const deptCounts = {};
  try {
    const courses = await apiRequest("/admin/courses");
    courses.forEach((c) => {
      deptCounts[c.department] = (deptCounts[c.department] || 0) + 1;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${c.course_id}</td><td>${escapeHtmlAdmin(c.course_code)}</td><td>${escapeHtmlAdmin(c.course_name)}</td><td>${c.credits}</td><td>${escapeHtmlAdmin(c.department)}</td>
        <td>
          <button type="button" class="secondary small" data-action="edit-course" data-course-id="${c.course_id}" data-code="${escapeHtmlAdmin(c.course_code)}" data-name="${escapeHtmlAdmin(c.course_name)}" data-credits="${c.credits}" data-department="${escapeHtmlAdmin(c.department)}">Edit</button>
          <button type="button" class="secondary small" data-action="delete-course" data-course-id="${c.course_id}">Delete</button>
        </td>`;
      coursesTbody.appendChild(tr);
    });
    const ctx = document.getElementById("courses-by-dept-chart");
    if (ctx && window.Chart) {
      if (window.adminDeptChart) window.adminDeptChart.destroy();
      window.adminDeptChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: Object.keys(deptCounts),
          datasets: [
            { label: "Courses", data: Object.values(deptCounts), backgroundColor: "#3b82f6" },
          ],
        },
        options: { responsive: true, plugins: { legend: { display: false } } },
      });
    }
  } catch { }

  const sectionsTbody = document.querySelector("#admin-sections-table tbody");
  if (sectionsTbody) sectionsTbody.innerHTML = "";
  try {
    const sections = await apiRequest("/admin/sections");
    sections.forEach((s) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${s.section_id}</td><td>${escapeHtmlAdmin(s.course_code)} – ${escapeHtmlAdmin(s.course_name)}</td><td>${escapeHtmlAdmin(s.instructor_name)}</td><td>${escapeHtmlAdmin(s.semester)}</td>
        <td>
          <button type="button" class="secondary small" data-action="edit-section" data-section-id="${s.section_id}" data-course-id="${s.course_id}" data-instructor-id="${s.instructor_id != null ? s.instructor_id : ""}" data-semester="${escapeHtmlAdmin(s.semester)}">Edit</button>
          <button type="button" class="secondary small" data-action="delete-section" data-section-id="${s.section_id}">Delete</button>
        </td>`;
      sectionsTbody.appendChild(tr);
    });
  } catch { }

  const schedulesTbody = document.querySelector("#admin-schedules-table tbody");
  if (schedulesTbody) schedulesTbody.innerHTML = "";
  try {
    const schedules = await apiRequest("/admin/schedules");
    schedules.forEach((s) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${s.schedule_id}</td><td>${s.section_id}</td><td>${escapeHtmlAdmin(s.day_of_week)}</td><td>${escapeHtmlAdmin(s.start_time)}</td><td>${escapeHtmlAdmin(s.end_time)}</td><td>${escapeHtmlAdmin(s.classroom_id)}</td>`;
      schedulesTbody.appendChild(tr);
    });
  } catch { }

  const instructorsTbody = document.querySelector("#admin-instructors-table tbody");
  if (instructorsTbody) instructorsTbody.innerHTML = "";
  try {
    const instructors = await apiRequest("/admin/instructors");
    instructors.forEach((i) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${i.instructor_id}</td><td>${escapeHtmlAdmin(i.name)}</td><td>${escapeHtmlAdmin(i.department)}</td>`;
      instructorsTbody.appendChild(tr);
    });
  } catch { }

  const roomsTbody = document.querySelector("#admin-classrooms-table tbody");
  if (roomsTbody) roomsTbody.innerHTML = "";
  try {
    const rooms = await apiRequest("/admin/classrooms");
    rooms.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${r.classroom_id}</td><td>${escapeHtmlAdmin(r.building)}</td><td>${r.room_number}</td><td>${r.capacity}</td>`;
      roomsTbody.appendChild(tr);
    });
  } catch { }

  const enrollmentsTbody = document.querySelector("#admin-enrollments-table tbody");
  if (enrollmentsTbody) enrollmentsTbody.innerHTML = "";
  try {
    const enrollments = await apiRequest("/admin/enrollments");
    enrollments.forEach((e) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtmlAdmin(e.student_name)} (#${e.student_id})</td><td>${escapeHtmlAdmin(e.course_code)} – ${escapeHtmlAdmin(e.course_name)}</td><td>${e.section_id}</td><td>${escapeHtmlAdmin(e.semester)}</td>`;
      enrollmentsTbody.appendChild(tr);
    });
  } catch { }
}

