#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MINIAPP = ROOT / "product" / "inner_world_v1" / "miniapp"
PORTABLE_ROOT = ROOT / "product" / "inner_world_v1" / "portable"
OUTPUT_DIR = PORTABLE_ROOT / "world-studio-portable"
ZIP_BASENAME = PORTABLE_ROOT / "world-studio-portable"


PORTABLE_BRIDGE_JS = dedent(
    r"""
    (() => {
      const STORAGE_KEY = "world-studio-portable.state.v1";
      const GRAPH_LAYER_ORDER = [
        "primitive",
        "character",
        "place",
        "object",
        "rule",
        "visual",
        "conflict",
        "relationship",
      ];
      const GRAPH_LAYER_LABELS = {
        primitive: "Emotional Core",
        character: "People",
        place: "Places",
        object: "Objects",
        rule: "Rules",
        visual: "Tone",
        conflict: "Pressure",
        relationship: "Connections",
      };
      const QUESTION_DEFS = {
        entrypoint: {
          question: "What feels easiest to start with?",
          layer: "meta",
          selection_mode: "single",
          allow_free_text: false,
          why_this_matters: "Starting from the easiest handle lowers cognitive load and gives the system a first anchor.",
          response_options: [
            { id: "emotion", label: "Start with the feeling", description: "Anchor the world in an emotional pressure first." },
            { id: "character", label: "Start with a person", description: "Give the world one human anchor before anything else." },
            { id: "place", label: "Start with a place", description: "Open on a location and let the world grow outward from it." },
            { id: "object", label: "Start with an object", description: "Use one meaningful object to pull the world into focus." },
            { id: "rule", label: "Start with a rule", description: "Define one law or binding condition the world obeys." },
          ],
        },
        core_emotion: {
          question: "What pressure sits at the center of this world?",
          layer: "primitive",
          selection_mode: "single",
          allow_free_text: true,
          why_this_matters: "The emotional core gives later places, objects, and conflicts something to echo.",
          response_options: [
            { id: "trust_fracture", label: "Fractured trust", description: "The world keeps testing what can be believed." },
            { id: "suppressed_grief", label: "Suppressed grief", description: "Loss is present, but socially compressed." },
            { id: "ritual_desire", label: "Ritual desire", description: "People want meaning badly enough to perform it into being." },
          ],
        },
        anchor_character: {
          question: "Who is one person this world can keep returning to?",
          layer: "character",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "One human anchor keeps the world from turning into abstract lore.",
          response_options: [],
        },
        anchor_place: {
          question: "What place makes the world feel concrete?",
          layer: "place",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "A place gives the world gravity, habit, and repeatable visual space.",
          response_options: [],
        },
        anchor_object: {
          question: "What object quietly carries the world's meaning?",
          layer: "object",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "A meaningful object becomes a bridge between theme and image.",
          response_options: [],
        },
        world_rule: {
          question: "What rule or condition binds this world?",
          layer: "rule",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "Rules create tension because every scene can test them.",
          response_options: [],
        },
        visual_tone: {
          question: "How should this world feel on screen?",
          layer: "visual",
          selection_mode: "single",
          allow_free_text: true,
          why_this_matters: "Visual tone keeps later shots from drifting into generic style.",
          response_options: [
            { id: "ritual_cold", label: "Ritual cold", description: "Wet stone, still frames, practical light, disciplined surfaces." },
            { id: "paper_white", label: "Paper white", description: "Matte pale materials, soft daylight, erased warmth." },
            { id: "reflective_stillness", label: "Reflective stillness", description: "Mirrors, glass, delayed motion, held reactions." },
          ],
        },
        core_conflict: {
          question: "What pressure is forcing the world to reveal itself?",
          layer: "conflict",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "Conflict is what turns worldbuilding into scene energy.",
          response_options: [],
        },
        connection_probe: {
          question: "What connection ties these fragments together in a way the audience can feel?",
          layer: "relationship",
          selection_mode: "free_text",
          allow_free_text: true,
          why_this_matters: "Connections make the world reusable because future scenes can traverse them.",
          response_options: [],
        },
      };
      const ENTRY_TO_QUESTION = {
        emotion: "core_emotion",
        character: "anchor_character",
        place: "anchor_place",
        object: "anchor_object",
        rule: "world_rule",
      };
      const REQUIRED_LAYERS = ["primitive", "character", "place", "object", "rule", "visual", "conflict"];
      const realFetch = window.fetch.bind(window);

      function deepClone(value) {
        return JSON.parse(JSON.stringify(value));
      }

      function nowIso() {
        return new Date().toISOString();
      }

      function makeId(prefix) {
        return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
      }

      function slugify(text) {
        return String(text || "")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "")
          .slice(0, 48);
      }

      function optionLabel(questionId, optionId) {
        const question = QUESTION_DEFS[questionId];
        return question?.response_options?.find((row) => row.id === optionId)?.label || optionId;
      }

      function extractLabel(text, fallback) {
        const candidate = String(text || "")
          .split(/[.!?]/)[0]
          .trim();
        if (!candidate) {
          return fallback;
        }
        const words = candidate.split(/\s+/).slice(0, 5).join(" ");
        return words || fallback;
      }

      function loadState() {
        const seeded = deepClone(window.WORLD_STUDIO_PORTABLE_SEED || {});
        try {
          const raw = window.localStorage.getItem(STORAGE_KEY);
          if (!raw) {
            return seeded;
          }
          const parsed = JSON.parse(raw);
          return {
            version: parsed.version || seeded.version || 1,
            worlds: Array.isArray(parsed.worlds) ? parsed.worlds : seeded.worlds || [],
            sessions: Array.isArray(parsed.sessions) ? parsed.sessions : seeded.sessions || [],
            packets: Array.isArray(parsed.packets) ? parsed.packets : seeded.packets || [],
          };
        } catch (_error) {
          return seeded;
        }
      }

      let state = loadState();

      function saveState() {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }

      function listWorlds() {
        return [...state.worlds]
          .sort((left, right) => String(right.updated_at || "").localeCompare(String(left.updated_at || "")))
          .map((world) => ({
            world_id: world.world_id,
            name: world.name,
            summary: world.summary,
            status: world.status || "active",
            updated_at: world.updated_at || nowIso(),
            packet_count: (world.packet_ids || []).length,
          }));
      }

      function getWorld(worldId) {
        const world = state.worlds.find((row) => row.world_id === worldId);
        if (!world) {
          throw new Error(`World not found: ${worldId}`);
        }
        return world;
      }

      function getSession(sessionId) {
        const session = state.sessions.find((row) => row.session_id === sessionId);
        if (!session) {
          throw new Error(`Population session not found: ${sessionId}`);
        }
        return session;
      }

      function activeSessionForWorld(worldId) {
        return state.sessions.find((row) => row.world_id === worldId && !row.completed) || null;
      }

      function coverageByLayer(world) {
        const coverage = {};
        for (const record of world.records || []) {
          if (!record.layer) {
            continue;
          }
          coverage[record.layer] = (coverage[record.layer] || 0) + 1;
        }
        return coverage;
      }

      function knowledgePreview(world) {
        const coverage = coverageByLayer(world);
        return {
          coverage_by_layer: coverage,
          recent_insights: (world.records || []).slice(-3).map((record) => record.label),
          inferred_connection_count: (world.connections || []).length,
          uncovered_layers: GRAPH_LAYER_ORDER.filter((layer) => !coverage[layer]),
        };
      }

      function questionOrder(entryChoice) {
        const prioritized = ENTRY_TO_QUESTION[entryChoice] || "anchor_object";
        const base = [
          "core_emotion",
          "anchor_character",
          "anchor_place",
          "anchor_object",
          "world_rule",
          "visual_tone",
          "core_conflict",
          "connection_probe",
        ];
        return ["entrypoint", prioritized, ...base.filter((row) => row !== prioritized)];
      }

      function nextQuestionId(session) {
        const order = questionOrder(session.entry_choice || "object");
        return order.find((row) => !session.answers[row]) || null;
      }

      function parseAnswer(questionId, answer) {
        const raw = String(answer || "").trim();
        if (!raw) {
          throw new Error("Answer required");
        }
        const question = QUESTION_DEFS[questionId];
        if (question?.selection_mode === "free_text") {
          return { raw, text: raw, choice: "", note: "" };
        }
        if (!raw.includes("|")) {
          return { raw, text: raw, choice: raw, note: "" };
        }
        const [choice, ...rest] = raw.split("|");
        const note = rest.join("|").trim();
        return {
          raw,
          text: note || optionLabel(questionId, choice.trim()),
          choice: choice.trim(),
          note,
        };
      }

      function recordForAnswer(questionId, parsed) {
        const common = {
          knowledge_id: makeId("knowledge"),
          created_at: nowIso(),
          tags: [],
          metadata: {
            source: "portable_mock",
            question_id: questionId,
          },
        };
        if (questionId === "core_emotion") {
          return {
            ...common,
            layer: "primitive",
            label: parsed.choice ? optionLabel(questionId, parsed.choice) : extractLabel(parsed.text, "Core Emotion"),
            summary: parsed.note || parsed.text,
            tags: ["emotion", parsed.choice || slugify(parsed.text)],
          };
        }
        if (questionId === "anchor_character") {
          return {
            ...common,
            layer: "character",
            label: extractLabel(parsed.text, "Anchor Character"),
            summary: parsed.text,
            tags: ["character", "anchor"],
          };
        }
        if (questionId === "anchor_place") {
          return {
            ...common,
            layer: "place",
            label: extractLabel(parsed.text, "Anchor Place"),
            summary: parsed.text,
            tags: ["place", "anchor"],
          };
        }
        if (questionId === "anchor_object") {
          return {
            ...common,
            layer: "object",
            label: extractLabel(parsed.text, "Anchor Object"),
            summary: parsed.text,
            tags: ["object", "motif"],
          };
        }
        if (questionId === "world_rule") {
          return {
            ...common,
            layer: "rule",
            label: extractLabel(parsed.text, "World Rule"),
            summary: parsed.text,
            tags: ["rule", "binding"],
          };
        }
        if (questionId === "visual_tone") {
          return {
            ...common,
            layer: "visual",
            label: parsed.choice ? optionLabel(questionId, parsed.choice) : extractLabel(parsed.text, "Visual Tone"),
            summary: parsed.note || parsed.text,
            tags: ["visual", parsed.choice || slugify(parsed.text)],
          };
        }
        if (questionId === "core_conflict") {
          return {
            ...common,
            layer: "conflict",
            label: extractLabel(parsed.text, "Core Conflict"),
            summary: parsed.text,
            tags: ["conflict", "pressure"],
          };
        }
        if (questionId === "connection_probe") {
          return {
            ...common,
            layer: "relationship",
            label: "Binding Connection",
            summary: parsed.text,
            tags: ["relationship", "bridge"],
          };
        }
        return null;
      }

      function latestRecord(world, layer) {
        const records = (world.records || []).filter((row) => row.layer === layer);
        return records[records.length - 1] || null;
      }

      function addConnection(rows, left, right, reason, score = 0.62) {
        if (!left || !right) {
          return;
        }
        const pairKey = [left.knowledge_id, right.knowledge_id].sort().join("::");
        if (rows.some((row) => [row.left_knowledge_id, row.right_knowledge_id].sort().join("::") === pairKey)) {
          return;
        }
        rows.push({
          connection_id: makeId("connection"),
          connection_type: "inferred_world_link",
          left_knowledge_id: left.knowledge_id,
          right_knowledge_id: right.knowledge_id,
          score,
          reasons: [reason],
          shared_tags: [...new Set([...(left.tags || []), ...(right.tags || [])])].slice(0, 4),
        });
      }

      function rebuildConnections(world) {
        const rows = [];
        addConnection(rows, latestRecord(world, "primitive"), latestRecord(world, "object"), "Objects should carry emotional pressure.");
        addConnection(rows, latestRecord(world, "primitive"), latestRecord(world, "visual"), "Tone should reinforce the emotional core.");
        addConnection(rows, latestRecord(world, "character"), latestRecord(world, "place"), "People should feel grounded in repeatable space.");
        addConnection(rows, latestRecord(world, "conflict"), latestRecord(world, "rule"), "Conflict should stress the rule that binds the world.");
        addConnection(rows, latestRecord(world, "relationship"), latestRecord(world, "object"), "Connections often condense through a symbolic object.", 0.72);
        addConnection(rows, latestRecord(world, "relationship"), latestRecord(world, "character"), "Connections should stay attached to a human anchor.", 0.7);
        addConnection(rows, latestRecord(world, "relationship"), latestRecord(world, "place"), "Connections should be spatially legible.", 0.66);
        world.connections = rows;
      }

      function refreshWorld(world) {
        rebuildConnections(world);
        const coverage = coverageByLayer(world);
        world.population_overview = {
          knowledge_record_count: (world.records || []).length,
          connection_count: (world.connections || []).length,
          coverage_by_layer: coverage,
          ready_for_generation: REQUIRED_LAYERS.every((layer) => coverage[layer] > 0),
        };
        world.updated_at = nowIso();
        world.packet_ids = world.packet_ids || [];
        world.status = "active";
      }

      function questionPayload(session) {
        const world = getWorld(session.world_id);
        const questionId = session.current_question_id;
        const question = QUESTION_DEFS[questionId];
        return {
          session_id: session.session_id,
          world_id: world.world_id,
          world_name: world.name,
          question_index: Object.keys(session.answers || {}).length,
          question_id: questionId,
          question: question.question,
          selection_mode: question.selection_mode,
          allow_free_text: question.allow_free_text,
          response_options: question.response_options,
          why_this_matters: question.why_this_matters,
          progress: {
            questions_asked: Object.keys(session.answers || {}).length,
            minimum_questions: 6,
            target_questions: 8,
            covered_layers: Object.keys(coverageByLayer(world)).length,
          },
          knowledge_preview: knowledgePreview(world),
          completed: false,
        };
      }

      function createWorld({ name, summary }) {
        const worldId = `world-${slugify(name) || makeId("world")}`;
        const world = {
          world_id: worldId,
          name: name || "Untitled World",
          summary: summary || "A world seed waiting for its first fragments.",
          status: "active",
          updated_at: nowIso(),
          packet_ids: [],
          records: [],
          connections: [],
        };
        refreshWorld(world);
        state.worlds.unshift(world);
        saveState();
        return world;
      }

      function startPopulation(payload) {
        const world = payload.world_id ? getWorld(payload.world_id) : createWorld(payload);
        const existing = activeSessionForWorld(world.world_id);
        if (existing) {
          return questionPayload(existing);
        }
        const session = {
          session_id: makeId("portable-session"),
          world_id: world.world_id,
          created_at: nowIso(),
          updated_at: nowIso(),
          answers: {},
          entry_choice: "",
          current_question_id: "entrypoint",
          completed: false,
        };
        state.sessions.unshift(session);
        world.active_session_id = session.session_id;
        saveState();
        return questionPayload(session);
      }

      function answerPopulation(payload) {
        const session = getSession(payload.session_id);
        const world = getWorld(session.world_id);
        const questionId = session.current_question_id;
        if (!questionId) {
          throw new Error("Session has no pending question.");
        }
        const parsed = parseAnswer(questionId, payload.answer);
        session.answers[questionId] = parsed;
        session.updated_at = nowIso();
        if (questionId === "entrypoint") {
          session.entry_choice = parsed.choice || parsed.text || "object";
        } else {
          const record = recordForAnswer(questionId, parsed);
          if (record) {
            world.records.push(record);
          }
        }
        refreshWorld(world);
        const nextQuestion = nextQuestionId(session);
        if (!nextQuestion) {
          session.completed = true;
          session.current_question_id = null;
          world.active_session_id = "";
          saveState();
          return {
            session_id: session.session_id,
            world_id: world.world_id,
            completed: true,
            status: "ready_for_generation",
            summary: {
              world_name: world.name,
              knowledge_record_count: (world.records || []).length,
              connection_count: (world.connections || []).length,
              coverage_by_layer: coverageByLayer(world),
              bridge_object_count: Math.min(3, (world.connections || []).length),
            },
          };
        }
        session.current_question_id = nextQuestion;
        world.active_session_id = session.session_id;
        saveState();
        return questionPayload(session);
      }

      function compileScene(payload) {
        const world = getWorld(payload.world_id);
        const packetId = makeId("packet");
        const packet = {
          packet_id: packetId,
          world_id: world.world_id,
          world_name: world.name,
          scene_text: String(payload.scene_text || "").trim(),
          status: "compiled",
          artifacts: [
            "context_packet",
            "higgsfield_execution_packet",
            "remotion_composition_props",
            "evaluation",
          ],
          created_at: nowIso(),
        };
        state.packets.unshift(packet);
        world.packet_ids = world.packet_ids || [];
        world.packet_ids.unshift(packetId);
        refreshWorld(world);
        saveState();
        return packet;
      }

      function layerClusterPosition(layer) {
        const index = Math.max(0, GRAPH_LAYER_ORDER.indexOf(layer));
        const angle = (-Math.PI / 2) + ((2 * Math.PI) / GRAPH_LAYER_ORDER.length) * index;
        const radius = 280;
        return { x: Math.round(Math.cos(angle) * radius * 10) / 10, y: Math.round(Math.sin(angle) * radius * 10) / 10 };
      }

      function recordPosition(layer, index) {
        const base = layerClusterPosition(layer);
        const fanAngle = -0.42 + (0.21 * index);
        const radial = 120 + (18 * Math.min(index, 4));
        return {
          x: Math.round((base.x + Math.cos(fanAngle) * radial) * 10) / 10,
          y: Math.round((base.y + Math.sin(fanAngle) * (radial * 0.68) + (index * 16)) * 10) / 10,
        };
      }

      function projectGraph(worldId) {
        const world = getWorld(worldId);
        refreshWorld(world);
        const coverage = coverageByLayer(world);
        const nodes = [
          {
            node_id: `world:${world.world_id}`,
            node_type: "world",
            layer: "world",
            label: world.name,
            summary: world.summary,
            layout: { x: 0, y: 0 },
            metadata: {
              ready_for_generation: !!world.population_overview?.ready_for_generation,
              packet_count: (world.packet_ids || []).length,
            },
          },
        ];
        const edges = [];
        for (const layer of GRAPH_LAYER_ORDER) {
          const position = layerClusterPosition(layer);
          const count = coverage[layer] || 0;
          nodes.push({
            node_id: `cluster:${layer}`,
            node_type: "cluster",
            layer,
            label: GRAPH_LAYER_LABELS[layer],
            summary: `${count} fragments`,
            layout: position,
            metadata: { count },
          });
          edges.push({
            edge_id: `edge:world:${layer}`,
            edge_type: "contains_layer",
            source_id: `world:${world.world_id}`,
            target_id: `cluster:${layer}`,
            weight: 0.42 + (0.05 * Math.min(count, 5)),
          });
        }
        const layerCounters = {};
        for (const record of world.records || []) {
          const index = layerCounters[record.layer] || 0;
          layerCounters[record.layer] = index + 1;
          nodes.push({
            node_id: record.knowledge_id,
            node_type: "fragment",
            layer: record.layer,
            label: record.label,
            summary: record.summary,
            tags: record.tags || [],
            layout: recordPosition(record.layer, index),
            metadata: record.metadata || {},
          });
          edges.push({
            edge_id: `edge:cluster:${record.layer}:${record.knowledge_id}`,
            edge_type: "belongs_to_layer",
            source_id: `cluster:${record.layer}`,
            target_id: record.knowledge_id,
            weight: 0.56,
          });
        }
        for (const connection of world.connections || []) {
          edges.push({
            edge_id: connection.connection_id,
            edge_type: connection.connection_type,
            source_id: connection.left_knowledge_id,
            target_id: connection.right_knowledge_id,
            weight: connection.score || 0.6,
            shared_tags: connection.shared_tags || [],
            reasons: connection.reasons || [],
          });
        }
        let focusNodeId = `world:${world.world_id}`;
        const session = activeSessionForWorld(world.world_id);
        if (session?.current_question_id) {
          const question = QUESTION_DEFS[session.current_question_id];
          const targetLayer = question.layer === "meta" ? "primitive" : question.layer;
          const questionId = `question:${session.session_id}:${session.current_question_id}`;
          nodes.push({
            node_id: questionId,
            node_type: "question",
            layer: question.layer,
            label: question.question,
            summary: question.why_this_matters,
            layout: { x: 0, y: -160 },
            metadata: {
              question_id: session.current_question_id,
              session_id: session.session_id,
              response_options: question.response_options,
              allow_free_text: question.allow_free_text,
              selection_mode: question.selection_mode,
            },
          });
          edges.push({
            edge_id: `edge:question:${session.current_question_id}`,
            edge_type: "asks_for",
            source_id: questionId,
            target_id: `cluster:${targetLayer}`,
            weight: 0.72,
          });
          focusNodeId = questionId;
        }
        const recommendedActions = [];
        if (session && !session.completed) {
          recommendedActions.push("continue_population");
        } else if (world.population_overview?.ready_for_generation) {
          recommendedActions.push("compile_scene");
        } else {
          recommendedActions.push("populate_world");
        }
        if ((world.records || []).length) {
          recommendedActions.push("inspect_node_graph");
        }
        if ((world.packet_ids || []).length) {
          recommendedActions.push("inspect_packets");
        }
        return {
          world_id: world.world_id,
          world_name: world.name,
          ready_for_generation: !!world.population_overview?.ready_for_generation,
          focus_node_id: focusNodeId,
          coverage_by_layer: coverage,
          nodes,
          edges,
          recommended_actions: recommendedActions,
          active_session_id: session?.session_id || "",
          packet_count: (world.packet_ids || []).length,
        };
      }

      function guidePayload() {
        return {
          title: "World Studio Portable Pack",
          summary: "This is a disconnected frontend slice of World Studio with a mock API bridge and seeded worlds for design work.",
          cli_commands: [
            "python3 serve_portable.py",
            "edit world-studio.html",
            "edit world-studio.css",
            "edit world-studio.js",
            "edit portable-mock-seed.js",
          ],
          recommended_workflow: [
            "Open the portable world studio in a local browser or preview surface.",
            "Adjust the UI in world-studio.html, world-studio.css, and world-studio.js.",
            "Use portable-mock-seed.js to create richer states for design review.",
            "Append your changes and merge advice to CHANGELOG.md before handing the folder back.",
            "On reimport, map the UI files back into the real Inner Space miniapp paths.",
          ],
        };
      }

      function worldKnowledge(worldId) {
        const world = getWorld(worldId);
        refreshWorld(world);
        return {
          world_id: world.world_id,
          world_name: world.name,
          knowledge_record_count: (world.records || []).length,
          connection_count: (world.connections || []).length,
          coverage_by_layer: coverageByLayer(world),
          records: deepClone(world.records || []),
          connections: deepClone(world.connections || []),
          world_snapshot: deepClone(world),
        };
      }

      function jsonResponse(payload, status = 200) {
        return new Response(JSON.stringify(payload), {
          status,
          headers: { "Content-Type": "application/json" },
        });
      }

      function normalizeWorldStudioPath(pathname) {
        const marker = "/world-studio";
        const index = pathname.indexOf(marker);
        return index >= 0 ? pathname.slice(index) : "";
      }

      function route(method, pathname, body) {
        if (pathname === "/world-studio/guide" && method === "GET") {
          return guidePayload();
        }
        if (pathname === "/world-studio/worlds" && method === "GET") {
          return { count: listWorlds().length, worlds: listWorlds() };
        }
        if (pathname === "/world-studio/world" && method === "POST") {
          return createWorld(body || {});
        }
        if (pathname === "/world-studio/population/start" && method === "POST") {
          return startPopulation(body || {});
        }
        if (pathname === "/world-studio/population/answer" && method === "POST") {
          return answerPopulation(body || {});
        }
        if (pathname === "/world-studio/compile-scene" && method === "POST") {
          return compileScene(body || {});
        }
        if (pathname.startsWith("/world-studio/world/") && pathname.endsWith("/graph") && method === "GET") {
          const worldId = decodeURIComponent(pathname.slice("/world-studio/world/".length, -"/graph".length).replace(/\/$/, ""));
          return projectGraph(worldId);
        }
        if (pathname.startsWith("/world-studio/world/") && pathname.endsWith("/knowledge") && method === "GET") {
          const worldId = decodeURIComponent(pathname.slice("/world-studio/world/".length, -"/knowledge".length).replace(/\/$/, ""));
          return worldKnowledge(worldId);
        }
        if (pathname.startsWith("/world-studio/world/") && method === "GET") {
          const worldId = decodeURIComponent(pathname.slice("/world-studio/world/".length).replace(/\/$/, ""));
          return deepClone(getWorld(worldId));
        }
        throw new Error(`No portable route for ${method} ${pathname}`);
      }

      window.WorldStudioPortable = {
        reset() {
          window.localStorage.removeItem(STORAGE_KEY);
          state = loadState();
          return deepClone(state);
        },
        exportState() {
          return deepClone(state);
        },
        importState(nextState) {
          state = deepClone(nextState);
          saveState();
          return deepClone(state);
        },
      };

      window.fetch = async function portableFetch(input, init = {}) {
        const url = typeof input === "string" ? input : input.url;
        const method = String(init.method || (typeof input !== "string" ? input.method : "GET") || "GET").toUpperCase();
        const parsed = new URL(url, window.location.href);
        const apiPath = normalizeWorldStudioPath(parsed.pathname);
        if (!apiPath) {
          return realFetch(input, init);
        }
        let body = {};
        const payloadText = init.body;
        if (typeof payloadText === "string" && payloadText.trim()) {
          try {
            body = JSON.parse(payloadText);
          } catch (_error) {
            body = {};
          }
        }
        try {
          const payload = route(method, apiPath, body);
          saveState();
          return jsonResponse(payload, 200);
        } catch (error) {
          return jsonResponse({ error: error instanceof Error ? error.message : String(error) }, 500);
        }
      };
    })();
    """
).strip() + "\n"


def generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def portable_seed_payload() -> dict:
    timestamp = generated_at()
    return {
        "version": 1,
        "generated_at": timestamp,
        "worlds": [
            {
                "world_id": "world-paper-lantern",
                "name": "Paper Lantern District",
                "summary": "A neighborhood that catalogues grief through household objects and borrowed light.",
                "status": "active",
                "updated_at": timestamp,
                "packet_ids": [],
                "records": [
                    {
                        "knowledge_id": "knowledge-paper-primitive",
                        "layer": "primitive",
                        "label": "Suppressed grief",
                        "summary": "Every room in the district is arranged to hold loss without naming it directly.",
                        "tags": ["emotion", "suppressed_grief"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-paper-character",
                        "layer": "character",
                        "label": "Nura Vale",
                        "summary": "Nura repairs paper lanterns for families who want memory to feel orderly again.",
                        "tags": ["character", "anchor"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-paper-place",
                        "layer": "place",
                        "label": "Lantern Registry Hall",
                        "summary": "A municipal hall where each household deposits one lantern for every loss it cannot publicly discuss.",
                        "tags": ["place", "anchor"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-paper-object",
                        "layer": "object",
                        "label": "Ash-lined lantern",
                        "summary": "A lantern whose paper darkens each time a family edits the story attached to it.",
                        "tags": ["object", "motif"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-paper-rule",
                        "layer": "rule",
                        "label": "Borrowed light must be returned",
                        "summary": "Any lantern lit with borrowed flame has to be extinguished before dawn or it begins carrying someone else's memory.",
                        "tags": ["rule", "binding"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-paper-visual",
                        "layer": "visual",
                        "label": "Paper white",
                        "summary": "Matte pale paper, diffused daylight, quiet wood, no decorative saturation.",
                        "tags": ["visual", "paper_white"],
                        "metadata": {"source": "portable_seed"},
                    },
                ],
                "connections": [],
                "active_session_id": "portable-session-paper-lantern",
            },
            {
                "world_id": "world-glass-harbor",
                "name": "Glass Harbor",
                "summary": "A port city where reflective surfaces are treated as evidence, not decoration.",
                "status": "active",
                "updated_at": "2026-05-04T12:00:00+00:00",
                "packet_ids": ["packet-glass-harbor-001", "packet-glass-harbor-002"],
                "records": [
                    {
                        "knowledge_id": "knowledge-glass-primitive",
                        "layer": "primitive",
                        "label": "Fractured trust",
                        "summary": "The city keeps asking people to perform certainty after the truth has already been edited.",
                        "tags": ["emotion", "trust_fracture"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-character",
                        "layer": "character",
                        "label": "Iris Vale",
                        "summary": "Iris is a civic archivist who recognizes tampering by the way reflection falls across rewritten ink.",
                        "tags": ["character", "anchor"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-place",
                        "layer": "place",
                        "label": "Tide Archive",
                        "summary": "A submerged records hall that stays dry only while the harbor bells are ringing.",
                        "tags": ["place", "anchor"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-object",
                        "layer": "object",
                        "label": "Salt-stained brass key",
                        "summary": "A key that should not open any living door, but keeps returning to Iris after each revision cycle.",
                        "tags": ["object", "motif"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-rule",
                        "layer": "rule",
                        "label": "Seawater oaths bind by dawn",
                        "summary": "Any oath spoken over seawater becomes physically binding once the next tide settles.",
                        "tags": ["rule", "binding"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-visual",
                        "layer": "visual",
                        "label": "Reflective stillness",
                        "summary": "Glass, wet stone, delayed reaction, practical light, no sentimental warmth.",
                        "tags": ["visual", "reflective_stillness"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-conflict",
                        "layer": "conflict",
                        "label": "The city edits memory to preserve civic calm",
                        "summary": "Iris can expose the manipulation, but doing so would invalidate the civic bonds that keep the harbor functioning.",
                        "tags": ["conflict", "pressure"],
                        "metadata": {"source": "portable_seed"},
                    },
                    {
                        "knowledge_id": "knowledge-glass-relationship",
                        "layer": "relationship",
                        "label": "Binding Connection",
                        "summary": "The brass key opens the Tide Archive, and every opening costs Iris one memory the city would rather keep rewritten.",
                        "tags": ["relationship", "bridge"],
                        "metadata": {"source": "portable_seed"},
                    },
                ],
                "connections": [
                    {
                        "connection_id": "connection-glass-1",
                        "connection_type": "inferred_world_link",
                        "left_knowledge_id": "knowledge-glass-primitive",
                        "right_knowledge_id": "knowledge-glass-object",
                        "score": 0.71,
                        "reasons": ["Objects should carry emotional pressure."],
                        "shared_tags": ["emotion", "motif"],
                    },
                    {
                        "connection_id": "connection-glass-2",
                        "connection_type": "inferred_world_link",
                        "left_knowledge_id": "knowledge-glass-character",
                        "right_knowledge_id": "knowledge-glass-place",
                        "score": 0.67,
                        "reasons": ["People should feel grounded in repeatable space."],
                        "shared_tags": ["anchor"],
                    },
                    {
                        "connection_id": "connection-glass-3",
                        "connection_type": "inferred_world_link",
                        "left_knowledge_id": "knowledge-glass-conflict",
                        "right_knowledge_id": "knowledge-glass-rule",
                        "score": 0.69,
                        "reasons": ["Conflict should stress the rule that binds the world."],
                        "shared_tags": ["binding", "pressure"],
                    },
                    {
                        "connection_id": "connection-glass-4",
                        "connection_type": "inferred_world_link",
                        "left_knowledge_id": "knowledge-glass-relationship",
                        "right_knowledge_id": "knowledge-glass-character",
                        "score": 0.73,
                        "reasons": ["Connections should stay attached to a human anchor."],
                        "shared_tags": ["anchor", "bridge"],
                    },
                ],
                "active_session_id": "",
            },
        ],
        "sessions": [
            {
                "session_id": "portable-session-paper-lantern",
                "world_id": "world-paper-lantern",
                "created_at": "2026-05-04T18:10:00+00:00",
                "updated_at": timestamp,
                "answers": {
                    "entrypoint": {"raw": "place", "text": "place", "choice": "place", "note": ""},
                    "anchor_place": {
                        "raw": "The Lantern Registry Hall is where families deposit one lantern for every grief they are not allowed to speak aloud.",
                        "text": "The Lantern Registry Hall is where families deposit one lantern for every grief they are not allowed to speak aloud.",
                        "choice": "",
                        "note": "",
                    },
                    "core_emotion": {
                        "raw": "suppressed_grief|The district is organized around losses that must remain elegant and indirect.",
                        "text": "The district is organized around losses that must remain elegant and indirect.",
                        "choice": "suppressed_grief",
                        "note": "The district is organized around losses that must remain elegant and indirect.",
                    },
                    "anchor_character": {
                        "raw": "Nura repairs paper lanterns for households whose memories have started to contradict each other.",
                        "text": "Nura repairs paper lanterns for households whose memories have started to contradict each other.",
                        "choice": "",
                        "note": "",
                    },
                    "anchor_object": {
                        "raw": "An ash-lined lantern that darkens every time a family retells the same memory differently.",
                        "text": "An ash-lined lantern that darkens every time a family retells the same memory differently.",
                        "choice": "",
                        "note": "",
                    },
                    "world_rule": {
                        "raw": "Any lantern lit with borrowed flame must be extinguished by dawn or it begins carrying someone else's memory.",
                        "text": "Any lantern lit with borrowed flame must be extinguished by dawn or it begins carrying someone else's memory.",
                        "choice": "",
                        "note": "",
                    },
                    "visual_tone": {
                        "raw": "paper_white|Matte paper, pale interiors, diffused daylight, and no decorative saturation.",
                        "text": "Matte paper, pale interiors, diffused daylight, and no decorative saturation.",
                        "choice": "paper_white",
                        "note": "Matte paper, pale interiors, diffused daylight, and no decorative saturation.",
                    },
                },
                "entry_choice": "place",
                "current_question_id": "core_conflict",
                "completed": False,
            }
        ],
        "packets": [
            {
                "packet_id": "packet-glass-harbor-001",
                "world_id": "world-glass-harbor",
                "world_name": "Glass Harbor",
                "scene_text": "Iris unlocks the Tide Archive and realizes the city has been editing her memories.",
                "status": "compiled",
                "artifacts": ["context_packet", "higgsfield_execution_packet", "remotion_composition_props", "evaluation"],
                "created_at": "2026-05-04T11:00:00+00:00",
            },
            {
                "packet_id": "packet-glass-harbor-002",
                "world_id": "world-glass-harbor",
                "world_name": "Glass Harbor",
                "scene_text": "A customs clerk notices that every reflection in the harbor blinks a fraction late.",
                "status": "compiled",
                "artifacts": ["context_packet", "higgsfield_execution_packet", "remotion_composition_props", "evaluation"],
                "created_at": "2026-05-04T12:00:00+00:00",
            },
        ],
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_portable_html(source_html: str) -> str:
    target = (
        '    <script src="./runtime-config.js"></script>\n'
        '    <script src="./portable-mock-seed.js"></script>\n'
        '    <script src="./portable-mock-bridge.js"></script>\n'
        '    <script src="./world-studio.js" defer></script>\n'
    )
    return source_html.replace(
        '    <script src="./runtime-config.js"></script>\n    <script src="./world-studio.js" defer></script>\n',
        target,
    )


def launch_index_html() -> str:
    return dedent(
        """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>World Studio Portable Pack</title>
            <style>
              :root {
                --paper: #f4f0e8;
                --surface: #fbf8f1;
                --ink: #1d1a17;
                --ink-soft: #645b51;
                --line: rgba(45, 36, 30, 0.14);
              }
              * { box-sizing: border-box; }
              body {
                margin: 0;
                min-height: 100vh;
                padding: 32px 20px;
                font-family: system-ui, sans-serif;
                color: var(--ink);
                background: var(--paper);
              }
              .shell {
                max-width: 920px;
                margin: 0 auto;
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 28px;
              }
              h1, h2, p { margin-top: 0; }
              p { color: var(--ink-soft); line-height: 1.6; }
              .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
                margin-top: 18px;
              }
              .card {
                display: block;
                padding: 16px;
                border: 1px solid var(--line);
                border-radius: 14px;
                color: inherit;
                text-decoration: none;
                background: rgba(255, 255, 255, 0.52);
              }
              code {
                display: inline-block;
                margin-top: 6px;
                padding: 3px 8px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid var(--line);
                font-size: 0.88rem;
              }
            </style>
          </head>
          <body>
            <main class="shell">
              <h1>World Studio Portable Pack</h1>
              <p>
                This folder is a disconnected frontend slice of World Studio. It includes the current browser UI,
                a local mock API bridge, seeded demo worlds, and the handoff documents needed for another agent
                to work on the UI away from the full Inner Space repo.
              </p>
              <div class="grid">
                <a class="card" href="./world-studio.html">
                  <strong>Open the app</strong>
                  <p>Run the full portable world studio UI with mock state.</p>
                  <code>world-studio.html</code>
                </a>
                <a class="card" href="./START_HERE.md">
                  <strong>Start here</strong>
                  <p>Quick orientation, usage, and packaging rules.</p>
                  <code>START_HERE.md</code>
                </a>
                <a class="card" href="./AGENT_BRIEF.md">
                  <strong>Agent brief</strong>
                  <p>Identity, scope, rules, and the exact handoff prompt.</p>
                  <code>AGENT_BRIEF.md</code>
                </a>
                <a class="card" href="./INTEGRATION_NOTES.md">
                  <strong>Reimport map</strong>
                  <p>How the portable files map back into the real repo.</p>
                  <code>INTEGRATION_NOTES.md</code>
                </a>
              </div>
            </main>
          </body>
        </html>
        """
    ).strip() + "\n"


def start_here_md(timestamp: str) -> str:
    return dedent(
        f"""
        # Start Here

        This portable pack was generated from the Inner Space repo on `{timestamp}`.

        It is deliberately small and disconnected. The goal is to let another agent redesign or modify the World Studio frontend without needing the full backend, server runtime, or project history.

        ## What Is In This Folder

        - `world-studio.html`
        - `world-studio.css`
        - `world-studio.js`
        - `portable-mock-seed.js`
        - `portable-mock-bridge.js`
        - `runtime-config.js`
        - `serve_portable.py`
        - `AGENT_BRIEF.md`
        - `HANDOFF_PROMPT.txt`
        - `CHANGELOG.md`
        - `INTEGRATION_NOTES.md`

        ## Fastest Way To Use It

        1. Run:

           ```bash
           python3 serve_portable.py
           ```

        2. Open:

           ```text
           http://127.0.0.1:8765/world-studio.html
           ```

        ## Editing Scope

        Focus on these files:

        - `world-studio.html`
        - `world-studio.css`
        - `world-studio.js`

        Use these files only for portable simulation:

        - `portable-mock-seed.js`
        - `portable-mock-bridge.js`

        ## Before Handing The Folder Back

        1. Append a short entry to `CHANGELOG.md`
        2. Note any merge advice in `INTEGRATION_NOTES.md`
        3. Return the whole folder or the zip archive, not just individual files
        """
    ).strip() + "\n"


def agent_brief_md(timestamp: str) -> str:
    return dedent(
        f"""
        # Agent Brief

        Generated: `{timestamp}`

        ## Project Identity

        This is **World Studio**, a conversation-first worldbuilding interface inside the Inner Space project.

        Its job is not to be a generic admin dashboard. It should feel like a calm working table where fragments of a fictional world accumulate, connect, and become reusable for later scene generation.

        ## What This Portable Pack Represents

        This folder is a **frontend-only, mock-backed fraction** of the real system.

        It exists so you can:

        - redesign the UI
        - adjust layout and interaction
        - reshape language and pacing
        - test richer or cleaner states with mock data

        It does **not** need to preserve the full production backend.

        ## Design Direction

        - human, calm, spatial, legible
        - minimal, restrained, paper-and-ink
        - avoid AI-dashboard tropes
        - current question should be central
        - world fragments should visibly accumulate

        ## Editing Rules

        - keep the pack portable and static
        - do not add build-tool requirements unless necessary
        - prefer direct HTML, CSS, and JS edits
        - use `portable-mock-seed.js` to make UI states easier to inspect
        - if you add new files, document them in `CHANGELOG.md`

        ## Exact Handoff Prompt

        See `HANDOFF_PROMPT.txt`.
        """
    ).strip() + "\n"


def handoff_prompt_txt() -> str:
    return dedent(
        """
        Work only inside this portable folder.

        This is a disconnected frontend slice of World Studio from the Inner Space project. Treat it as a mock-backed UI sandbox, not as the full production repo.

        Primary goal:
        Improve the World Studio frontend experience while keeping the project identity intact: conversation-first, node-based, spatial, minimal, calm, and human.

        Important files:
        - world-studio.html
        - world-studio.css
        - world-studio.js
        - portable-mock-seed.js
        - portable-mock-bridge.js
        - CHANGELOG.md
        - INTEGRATION_NOTES.md

        Rules:
        - do not assume access to the full backend or the Inner Space repo
        - use the mock data and mock bridge to simulate states
        - if you change the UI, append a clear entry to CHANGELOG.md
        - if a change will matter during merge-back, explain it in INTEGRATION_NOTES.md
        - keep the output portable, static, and easy to hand back
        """
    ).strip() + "\n"


def changelog_md(timestamp: str) -> str:
    return dedent(
        f"""
        # Changelog

        ## 2026-05-05 - Portable pack created

        - extracted the current World Studio browser UI into a disconnected folder
        - added a local mock API bridge
        - added seeded worlds and packet states
        - added intro, handoff, and integration documents

        Files:
        - `world-studio.html`
        - `world-studio.css`
        - `world-studio.js`
        - `portable-mock-seed.js`
        - `portable-mock-bridge.js`
        - `START_HERE.md`
        - `AGENT_BRIEF.md`
        - `HANDOFF_PROMPT.txt`
        - `INTEGRATION_NOTES.md`

        Merge note:
        - production UI files in the real repo live under `product/inner_world_v1/miniapp/`

        ---

        ## Template For Future Entries

        ### YYYY-MM-DD - Short change title

        - what changed
        - why it changed
        - any design or interaction intent

        Files:
        - `changed-file-a`
        - `changed-file-b`

        Merge note:
        - anything the integration agent should watch for
        """
    ).strip() + "\n"


def integration_notes_md(timestamp: str) -> str:
    return dedent(
        f"""
        # Integration Notes

        Generated: `{timestamp}`

        ## Real Repo To Reimport Into

        Open this project when reintegrating:

        ```text
        /Users/talhauddin/software/inner_space
        ```

        ## Direct File Mapping

        Portable file -> Real repo file

        - `world-studio.html` -> `product/inner_world_v1/miniapp/world-studio.html`
        - `world-studio.css` -> `product/inner_world_v1/miniapp/world-studio.css`
        - `world-studio.js` -> `product/inner_world_v1/miniapp/world-studio.js`

        Portable-only support files:

        - `portable-mock-seed.js`
        - `portable-mock-bridge.js`
        - `serve_portable.py`
        - `START_HERE.md`
        - `AGENT_BRIEF.md`
        - `HANDOFF_PROMPT.txt`

        These support files do **not** need to be merged into production unless explicitly useful.

        ## Practical Merge Advice

        1. Compare the returned `world-studio.html`, `world-studio.css`, and `world-studio.js` against the current repo versions.
        2. Reapply good UI changes into the production miniapp files.
        3. Do not blindly copy the portable mock bridge into production.
        4. Use `CHANGELOG.md` from the returned folder as the first-pass merge summary.
        5. If the portable agent introduced new states or patterns, map them onto the real API responses instead of preserving mock-specific shortcuts.
        """
    ).strip() + "\n"


def serve_portable_py() -> str:
    return dedent(
        """
        #!/usr/bin/env python3
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        from pathlib import Path
        import os

        ROOT = Path(__file__).resolve().parent
        os.chdir(ROOT)

        server = ThreadingHTTPServer(("127.0.0.1", 8765), SimpleHTTPRequestHandler)
        print("Serving portable pack at http://127.0.0.1:8765/world-studio.html")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        """
    ).strip() + "\n"


def runtime_config_js() -> str:
    return 'window.INNER_WORLD_CONFIG = Object.assign({}, window.INNER_WORLD_CONFIG || {}, {"apiBaseUrl": "/api"});\n'


def manifest_json(timestamp: str) -> dict:
    return {
        "name": "world-studio-portable-pack",
        "generated_at": timestamp,
        "source_repo": str(ROOT),
        "source_ui_files": [
            "product/inner_world_v1/miniapp/world-studio.html",
            "product/inner_world_v1/miniapp/world-studio.css",
            "product/inner_world_v1/miniapp/world-studio.js",
        ],
        "reimport_targets": [
            "product/inner_world_v1/miniapp/world-studio.html",
            "product/inner_world_v1/miniapp/world-studio.css",
            "product/inner_world_v1/miniapp/world-studio.js",
        ],
    }


def build(output_dir: Path) -> dict:
    timestamp = generated_at()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SOURCE_MINIAPP / "world-studio.css", output_dir / "world-studio.css")
    shutil.copy2(SOURCE_MINIAPP / "world-studio.js", output_dir / "world-studio.js")
    portable_html = build_portable_html((SOURCE_MINIAPP / "world-studio.html").read_text(encoding="utf-8"))
    write_text(output_dir / "world-studio.html", portable_html)
    write_text(output_dir / "index.html", launch_index_html())
    write_text(output_dir / "runtime-config.js", runtime_config_js())
    write_text(output_dir / "portable-mock-bridge.js", PORTABLE_BRIDGE_JS)
    seed_js = "window.WORLD_STUDIO_PORTABLE_SEED = " + json.dumps(portable_seed_payload(), indent=2, ensure_ascii=False) + ";\n"
    write_text(output_dir / "portable-mock-seed.js", seed_js)
    write_text(output_dir / "START_HERE.md", start_here_md(timestamp))
    write_text(output_dir / "AGENT_BRIEF.md", agent_brief_md(timestamp))
    write_text(output_dir / "HANDOFF_PROMPT.txt", handoff_prompt_txt())
    write_text(output_dir / "CHANGELOG.md", changelog_md(timestamp))
    write_text(output_dir / "INTEGRATION_NOTES.md", integration_notes_md(timestamp))
    write_text(output_dir / "serve_portable.py", serve_portable_py())
    write_text(output_dir / "portable-pack.json", json.dumps(manifest_json(timestamp), indent=2, ensure_ascii=False) + "\n")

    if ZIP_BASENAME.with_suffix(".zip").exists():
        ZIP_BASENAME.with_suffix(".zip").unlink()
    archive_path = Path(shutil.make_archive(str(ZIP_BASENAME), "zip", root_dir=output_dir.parent, base_dir=output_dir.name))
    return {
        "output_dir": str(output_dir),
        "zip_path": str(archive_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a portable World Studio frontend pack with mock state.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()
    payload = build(Path(args.output_dir).expanduser().resolve())
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
