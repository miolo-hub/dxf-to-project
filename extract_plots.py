#!/usr/bin/env python3
"""Polygonize Chandamama Phase-2 layout lines into plot faces."""
import json
import math
from collections import defaultdict

SRC = "/Users/karthikeya/Downloads/chandamama_phase2_layout.json"
# 7/170 are the outer boundary; 8/10 are plot and road lines.
COLORS = {7, 8, 10, 170, 210, 254}
MIN_LEN = 2.0
TOL = 0.2  # endpoint-on-segment join distance
SNAP = 0.05


def dist_point_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1), 0.0
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    tc = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + tc * dx), py - (y1 + tc * dy)), t


def load_segments():
    data = json.load(open(SRC))
    segs = []
    for e in data["entities"]:
        if e["colorIndex"] not in COLORS:
            continue
        vs = e["vertices"]
        pts = vs + ([vs[0]] if e.get("closed") and len(vs) > 2 else [])
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]["x"], pts[i]["y"]
            x2, y2 = pts[i + 1]["x"], pts[i + 1]["y"]
            L = math.hypot(x2 - x1, y2 - y1)
            # ponytail: drop diagonal ticks inside plots; boundaries are axis-aligned
            if L >= MIN_LEN and (abs(x2 - x1) < 0.18 * L or abs(y2 - y1) < 0.18 * L):
                segs.append([x1, y1, x2, y2])
    return segs


def split_segments(segs):
    splits = [[] for _ in segs]
    n = len(segs)
    for i in range(n):
        ax, ay, bx, by = segs[i]
        for j in range(i + 1, n):
            cx, cy, dx, dy = segs[j]
            # endpoint of j near segment i, and vice versa, plus proper crossings
            hits = []
            for px, py, owner in ((ax, ay, i), (bx, by, i), (cx, cy, j), (dx, dy, j)):
                other = j if owner == i else i
                ox1, oy1, ox2, oy2 = segs[other]
                d, t = dist_point_seg(px, py, ox1, oy1, ox2, oy2)
                if d <= TOL and -0.02 <= t <= 1.02:
                    hits.append((other, max(0.0, min(1.0, t))))
            # proper intersection
            rxx, rxy = bx - ax, by - ay
            sxx, sxy = dx - cx, dy - cy
            den = rxx * sxy - rxy * sxx
            if abs(den) > 1e-9:
                t = ((cx - ax) * sxy - (cy - ay) * sxx) / den
                u = ((cx - ax) * rxy - (cy - ay) * rxx) / den
                if -0.01 <= t <= 1.01 and -0.01 <= u <= 1.01:
                    hits.append((i, max(0.0, min(1.0, t))))
                    hits.append((j, max(0.0, min(1.0, u))))
            for owner, t in hits:
                splits[owner].append(t)
    out = []
    for (x1, y1, x2, y2), ts in zip(segs, splits):
        ts = [0.0, 1.0] + ts
        ts = sorted(set(round(t, 5) for t in ts))
        for a, b in zip(ts, ts[1:]):
            if b - a < 1e-4:
                continue
            ax, ay = x1 + a * (x2 - x1), y1 + a * (y2 - y1)
            bx, by = x1 + b * (x2 - x1), y1 + b * (y2 - y1)
            if math.hypot(bx - ax, by - ay) < 0.35:
                continue
            out.append((ax, ay, bx, by))
    return out


def snap(x, y):
    return (round(x / SNAP) * SNAP, round(y / SNAP) * SNAP)


def build_graph(pieces):
    edges = set()
    for x1, y1, x2, y2 in pieces:
        a, b = snap(x1, y1), snap(x2, y2)
        if a != b:
            edges.add(tuple(sorted((a, b))))
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def faces_from(adj):
    ordered = {}
    for v, ns in adj.items():
        ordered[v] = sorted(ns, key=lambda n: math.atan2(n[1] - v[1], n[0] - v[0]))

    def nxt(u, v):
        ns = ordered[v]
        try:
            i = ns.index(u)
        except ValueError:
            return None
        return ns[(i - 1) % len(ns)]

    used = set()
    faces = []
    for a, ns in ordered.items():
        for b in ns:
            if (a, b) in used:
                continue
            start = (a, b)
            u, v = a, b
            poly = [a]
            guard = 0
            ok = False
            while guard < 8000:
                guard += 1
                if (u, v) in used and (u, v) != start:
                    break
                used.add((u, v))
                poly.append(v)
                w = nxt(u, v)
                if w is None:
                    break
                u, v = v, w
                if (u, v) == start:
                    ok = True
                    break
            if ok and len(poly) >= 4:
                faces.append(poly[:-1])
    return faces


def shoelace(poly):
    a = 0.0
    for i, (x, y) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x * y2 - x2 * y
    return a / 2


def main():
    segs = load_segments()
    print("raw segs", len(segs))
    pieces = split_segments(segs)
    print("pieces", len(pieces))
    adj = build_graph(pieces)
    print("verts", len(adj), "edges", sum(len(v) for v in adj.values()) // 2)
    deg = defaultdict(int)
    for v, ns in adj.items():
        deg[len(ns)] += 1
    print("degree", dict(sorted(deg.items())))
    faces = faces_from(adj)
    stats = []
    for poly in faces:
        area = shoelace(poly)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        stats.append((abs(area), area, w, h, len(poly)))
    stats.sort()
    print("faces", len(stats))
    if stats:
        print("smallest", stats[:8])
        print("largest", stats[-5:])
        buckets = defaultdict(int)
        for a, *_ in stats:
            if a < 2:
                buckets["<2"] += 1
            elif a < 8:
                buckets["2-8"] += 1
            elif a < 30:
                buckets["8-30"] += 1
            elif a < 80:
                buckets["30-80"] += 1
            elif a < 200:
                buckets["80-200"] += 1
            else:
                buckets["200+"] += 1
        print("areas", dict(buckets))


if __name__ == "__main__":
    main()
