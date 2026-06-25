import argparse
import json
import os
import html
import difflib

def compute_inline_diff(s1, s2):
    """
    Performs a character-level sequence evaluation on two matching lines.
    Handles structural line additions and omissions safely without dropping text.
    """
    if s1 is None and s2 is None:
        return "", ""
    if s1 is None:
        return "", html.escape(s2)
    if s2 is None:
        return html.escape(s1), ""
    
    sm = difflib.SequenceMatcher(None, s1, s2)
    res1 = []
    res2 = []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            res1.append(html.escape(s1[i1:i2]))
            res2.append(html.escape(s2[j1:j2]))
        elif tag == 'replace':
            res1.append(f'<span class="inline-del">{html.escape(s1[i1:i2])}</span>')
            res2.append(f'<span class="inline-add">{html.escape(s2[j1:j2])}</span>')
        elif tag == 'delete':
            res1.append(f'<span class="inline-del">{html.escape(s1[i1:i2])}</span>')
        elif tag == 'insert':
            res2.append(f'<span class="inline-add">{html.escape(s2[j1:j2])}</span>')
            
    return "".join(res1), "".join(res2)

def generate_merge_html(file1_path, file2_path, output_path):
    with open(file1_path, 'r', encoding='utf-8', errors='replace') as f:
        file1_lines = [line.rstrip('\n') for line in f.readlines()]
    with open(file2_path, 'r', encoding='utf-8', errors='replace') as f:
        file2_lines = [line.rstrip('\n') for line in f.readlines()]

    sm = difflib.SequenceMatcher(None, file1_lines, file2_lines)
    aligned_rows = []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                aligned_rows.append({
                    "type": "equal", "sym": "=",
                    "f1_raw": file1_lines[i1 + k], "ln1": i1 + k + 1,
                    "f2_raw": file2_lines[j1 + k], "ln2": j1 + k + 1
                })
        elif tag == 'replace':
            idx1, idx2 = i1, j1
            # Look-ahead pairing engine to map shifted modifications amidst large insertions/deletions
            while idx1 < i2 or idx2 < j2:
                if idx1 < i2 and idx2 < j2:
                    found_match_idx2 = None
                    best_sim = 0.4  # Alignment threshold
                    
                    for look_idx2 in range(idx2, j2):
                        sim = difflib.SequenceMatcher(None, file1_lines[idx1], file2_lines[look_idx2]).ratio()
                        if sim >= best_sim:
                            best_sim = sim
                            found_match_idx2 = look_idx2
                            if sim > 0.7:  # Strong anchor found, lock alignment target
                                break
                    
                    if found_match_idx2 is not None:
                        # Flush out intervening lines from modified file as clean additions
                        for k in range(idx2, found_match_idx2):
                            aligned_rows.append({
                                "type": "added", "sym": "+",
                                "f1_raw": None, "ln1": "",
                                "f2_raw": file2_lines[k], "ln2": k + 1
                            })
                        
                        sim_match = difflib.SequenceMatcher(None, file1_lines[idx1], file2_lines[found_match_idx2]).ratio()
                        row_type = "equal" if sim_match == 1.0 else "changed"
                        row_sym = "=" if sim_match == 1.0 else "~"
                        
                        aligned_rows.append({
                            "type": row_type, "sym": row_sym,
                            "f1_raw": file1_lines[idx1], "ln1": idx1 + 1,
                            "f2_raw": file2_lines[found_match_idx2], "ln2": found_match_idx2 + 1
                        })
                        idx2 = found_match_idx2 + 1
                        idx1 += 1
                    else:
                        # No candidate lines ahead match, process original line as a direct removal
                        aligned_rows.append({
                            "type": "removed", "sym": "-",
                            "f1_raw": file1_lines[idx1], "ln1": idx1 + 1,
                            "f2_raw": None, "ln2": ""
                        })
                        idx1 += 1
                elif idx1 < i2:
                    aligned_rows.append({
                        "type": "removed", "sym": "-",
                        "f1_raw": file1_lines[idx1], "ln1": idx1 + 1,
                        "f2_raw": None, "ln2": ""
                    })
                    idx1 += 1
                elif idx2 < j2:
                    aligned_rows.append({
                        "type": "added", "sym": "+",
                        "f1_raw": None, "ln1": "",
                        "f2_raw": file2_lines[idx2], "ln2": idx2 + 1
                    })
                    idx2 += 1
        elif tag == 'delete':
            for k in range(i1, i2):
                aligned_rows.append({
                    "type": "removed", "sym": "-",
                    "f1_raw": file1_lines[k], "ln1": k + 1,
                    "f2_raw": None, "ln2": ""
                })
        elif tag == 'insert':
            for k in range(j1, j2):
                aligned_rows.append({
                    "type": "added", "sym": "+",
                    "f1_raw": None, "ln1": "",
                    "f2_raw": file2_lines[k], "ln2": k + 1
                })

    payload = []
    for row in aligned_rows:
        f1_html, f2_html = compute_inline_diff(row["f1_raw"], row["f2_raw"])
        payload.append({
            "type": row["type"],
            "sym": row["sym"],
            "f1_raw": row["f1_raw"],
            "f1_html": f1_html,
            "ln1": row["ln1"],
            "f2_raw": row["f2_raw"],
            "f2_html": f2_html,
            "ln2": row["ln2"]
        })

    rows_json = json.dumps(payload)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>High Fidelity Merge Workspace</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f6f8fa;
            color: #24292e;
            display: flex;
            flex-direction: column;
            height: 100vh;
            box-sizing: border-box;
        }}
        .controls {{
            background: #ffffff;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }}
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .controls input {{
            width: 60px;
            padding: 6px;
            font-size: 14px;
            border: 1px solid #d1d5da;
            border-radius: 4px;
        }}
        button {{
            padding: 6px 12px;
            font-size: 14px;
            font-weight: bold;
            background-color: #24292e;
            color: #fff;
            border: 1px solid rgba(27,31,35,0.15);
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{ background-color: #1f2327; }}
        .save-btn {{ background-color: #2ea44f; }}
        .save-btn:hover {{ background-color: #2c974b; }}
        
        .workspace {{
            display: flex;
            gap: 10px;
            flex-grow: 1;
            overflow-y: auto; /* Master common vertical scrollbar */
            padding-bottom: 20px;
        }}
        .column {{
            flex: 1;
            background: #ffffff;
            border: 1px solid #d1d5da;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
        }}
        .column-header {{
            background: #f1f2f4;
            padding: 10px;
            font-weight: bold;
            border-bottom: 1px solid #d1d5da;
            text-align: center;
            user-select: none;
            position: sticky; /* Keep panels aligned cleanly while scrolling */
            top: 0;
            z-index: 10;
        }}
        .table-container {{
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
            font-size: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }}
        td {{
            padding: 4px 8px;
            white-space: pre-wrap;
            word-break: break-all;
            height: 20px;
            vertical-align: top;
        }}
        .ln-cell {{
            width: 40px;
            text-align: right;
            color: #6a737d;
            background-color: #fafbfc;
            border-right: 1px solid #e1e4e8;
            padding-right: 6px;
            user-select: none;
        }}
        .sym-cell {{
            width: 25px;
            text-align: center;
            user-select: none;
            border-right: 1px solid #e1e4e8;
            font-weight: bold;
        }}
        .action-cell {{
            width: 40px;
            text-align: center;
            user-select: none;
        }}
        .merge-action-btn {{
            cursor: pointer;
            background: #e1e4e8;
            border: 1px solid #d1d5da;
            border-radius: 3px;
            padding: 1px 6px;
            font-size: 11px;
            font-weight: bold;
        }}
        .merge-action-btn:hover {{
            background: #0366d6;
            color: #fff;
        }}
        
        .equal {{ background-color: #ffffff; color: #24292e; }}
        .added {{ background-color: #e6ffed; color: #22863a; }}
        .removed {{ background-color: #ffeef0; color: #cb2431; }}
        .changed {{ background-color: #fff8e1; color: #b07d00; }}
        .empty-line {{ background-color: #fafbfc; color: #959da5; }}

        .merged-accepted {{
            background-color: #dbedff;
            color: #0366d6;
            font-weight: 500;
        }}

        .inline-add {{
            background-color: #acf2bd;
            font-weight: bold;
            border-radius: 2px;
            padding: 0 2px;
        }}
        .inline-del {{
            background-color: #fdb8c0;
            text-decoration: line-through;
            border-radius: 2px;
            padding: 0 2px;
        }}

        summary {{
            padding: 8px;
            background: #f6f8fa;
            cursor: pointer;
            border-bottom: 1px solid #d1d5da;
            font-weight: bold;
            user-select: none;
            font-size: 12px;
        }}
        details {{ border-bottom: 1px solid #d1d5da; }}
    </style>
</head>
<body>

    <div class="controls">
        <div class="control-group">
            <label for="contextLines">Context Lines around changes:</label>
            <input type="number" id="contextLines" value="5" min="0">
            <button onclick="renderPanels()">Apply Window</button>
        </div>
        <div>
            <button class="save-btn" onclick="saveMergedFile()">💾 Save Merged File</button>
        </div>
    </div>

    <div class="workspace">
        <div class="column">
            <div class="column-header">Original Document (Left)</div>
            <div class="table-container" id="leftContainer"></div>
        </div>
        
        <div class="column">
            <div class="column-header">Merged Result (Center)</div>
            <div class="table-container" id="centerContainer"></div>
        </div>
        
        <div class="column">
            <div class="column-header">Modified Document (Right)</div>
            <div class="table-container" id="rightContainer"></div>
        </div>
    </div>

    <script type="application/json" id="rawDiffData">{rows_json}</script>

    <script>
        const rawDiffData = JSON.parse(document.getElementById('rawDiffData').textContent);
        
        let mergedState = rawDiffData.map(row => {{
            if (row.type === 'equal') {{
                return {{ text: row.f1_raw, status: 'accepted' }};
            }}
            return {{ text: null, status: 'pending' }};
        }});

        function setMergeValue(index, source) {{
            const row = rawDiffData[index];
            if (source === 'left') {{
                mergedState[index] = {{ text: row.f1_raw, status: 'accepted' }};
            }} else if (source === 'right') {{
                mergedState[index] = {{ text: row.f2_raw, status: 'accepted' }};
            }}
            renderPanels();
        }}

        function declineMergeValue(index) {{
            mergedState[index] = {{ text: null, status: 'declined' }};
            renderPanels();
        }}

        function resetMergeValue(index) {{
            mergedState[index] = {{ text: null, status: 'pending' }};
            renderPanels();
        }}

        function renderPanels() {{
            const contextLimit = parseInt(document.getElementById('contextLines').value) || 0;
            
            const leftContainer = document.getElementById('leftContainer');
            const centerContainer = document.getElementById('centerContainer');
            const rightContainer = document.getElementById('rightContainer');

            leftContainer.innerHTML = '';
            centerContainer.innerHTML = '';
            rightContainer.innerHTML = '';

            const totalRows = rawDiffData.length;
            
            let centerLineNumbers = new Array(totalRows).fill("");
            let currentLineCount = 1;
            for (let i = 0; i < totalRows; i++) {{
                if (mergedState[i].status === 'accepted' && mergedState[i].text !== null) {{
                    centerLineNumbers[i] = currentLineCount++;
                }}
            }}

            const visibleFlags = new Array(totalRows).fill(false);
            for (let i = 0; i < totalRows; i++) {{
                if (rawDiffData[i].type !== 'equal') {{
                    let start = Math.max(0, i - contextLimit);
                    let end = Math.min(totalRows - 1, i + contextLimit);
                    for (let j = start; j <= end; j++) {{
                        visibleFlags[j] = true;
                    }}
                }}
            }}

            let currentBlock = null;
            let blocks = [];
            for (let i = 0; i < totalRows; i++) {{
                const type = visibleFlags[i] ? 'visible' : 'collapsed';
                if (!currentBlock || currentBlock.type !== type) {{
                    currentBlock = {{ type: type, startIndex: i, length: 0 }};
                    blocks.push(currentBlock);
                }}
                currentBlock.length++;
            }}

            let blockCount = 0;

            blocks.forEach(block => {{
                if (block.type === 'visible') {{
                    const leftTable = document.createElement('table');
                    const centerTable = document.createElement('table');
                    const rightTable = document.createElement('table');

                    for (let i = block.startIndex; i < block.startIndex + block.length; i++) {{
                        const row = rawDiffData[i];
                        
                        // Left Column
                        const trL = document.createElement('tr');
                        if (row.f1_raw !== null) {{
                            trL.className = row.type;
                            
                            const tdLn = document.createElement('td'); tdLn.className = 'ln-cell'; tdLn.textContent = row.ln1; trL.appendChild(tdLn);
                            const tdSym = document.createElement('td'); tdSym.className = 'sym-cell'; tdSym.textContent = row.sym; trL.appendChild(tdSym);
                            const tdTxt = document.createElement('td'); tdTxt.innerHTML = row.f1_html; trL.appendChild(tdTxt);
                            
                            const tdAct = document.createElement('td'); tdAct.className = 'action-cell';
                            if (row.type !== 'equal') {{
                                const btn = document.createElement('button');
                                btn.className = 'merge-action-btn';
                                btn.textContent = '➔';
                                btn.onclick = function() {{ setMergeValue(i, 'left'); }};
                                tdAct.appendChild(btn);
                            }}
                            trL.appendChild(tdAct);
                        }} else {{
                            trL.className = 'empty-line';
                            trL.innerHTML = '<td class="ln-cell"></td><td class="sym-cell"></td><td></td><td class="action-cell"></td>';
                        }}
                        leftTable.appendChild(trL);

                        // Center Column
                        const trC = document.createElement('tr');
                        const state = mergedState[i];
                        
                        const tdCLn = document.createElement('td'); tdCLn.className = 'ln-cell'; tdCLn.textContent = centerLineNumbers[i]; trC.appendChild(tdCLn);
                        const tdCAct = document.createElement('td'); tdCAct.className = 'action-cell';
                        
                        if (row.type !== 'equal' && state.status !== 'pending') {{
                            const undoBtn = document.createElement('button');
                            undoBtn.className = 'merge-action-btn';
                            undoBtn.style.backgroundColor = '#ffffff';
                            undoBtn.style.borderColor = '#d1d5da';
                            undoBtn.textContent = '↩';
                            undoBtn.title = 'Undo merge adjustment';
                            undoBtn.onclick = function() {{ resetMergeValue(i); }};
                            tdCAct.appendChild(undoBtn);
                        }}
                        trC.appendChild(tdCAct);
                        
                        const tdCTxt = document.createElement('td');
                        if (state.status === 'accepted') {{
                            trC.className = (row.type !== 'equal') ? 'merged-accepted' : 'equal';
                            tdCTxt.textContent = state.text;
                        }} else if (state.status === 'pending') {{
                            trC.className = 'changed';
                            tdCTxt.style.display = 'flex';
                            tdCTxt.style.justifyContent = 'space-between';
                            tdCTxt.style.alignItems = 'center';
                            
                            const span = document.createElement('span');
                            span.style.fontStyle = 'italic';
                            span.style.color = '#a0a0a0';
                            span.textContent = '[Pending Choice]';
                            tdCTxt.appendChild(span);
                            
                            const btn = document.createElement('button');
                            btn.className = 'merge-action-btn';
                            btn.style.background = '#ffffff';
                            btn.style.borderColor = '#cb2431';
                            btn.style.color = '#cb2431';
                            btn.style.fontSize = '12px';
                            btn.style.padding = '0px 5px';
                            btn.title = 'Omit line completely';
                            btn.textContent = '∅';
                            btn.onclick = function() {{ declineMergeValue(i); }};
                            tdCTxt.appendChild(btn);
                        }} else {{
                            trC.className = 'empty-line';
                            tdCTxt.style.fontStyle = 'italic';
                            tdCTxt.style.color = '#8c8c8c';
                            tdCTxt.style.backgroundColor = '#f0f0f0';
                            tdCTxt.textContent = '[Line Omitted]';
                        }}
                        trC.appendChild(tdCTxt);
                        centerTable.appendChild(trC);

                        // Right Column
                        const trR = document.createElement('tr');
                        if (row.f2_raw !== null) {{
                            trR.className = row.type;
                            
                            const tdAct = document.createElement('td'); tdAct.className = 'action-cell';
                            if (row.type !== 'equal') {{
                                const btn = document.createElement('button');
                                btn.className = 'merge-action-btn';
                                btn.textContent = '⬅';
                                btn.onclick = function() {{ setMergeValue(i, 'right'); }};
                                tdAct.appendChild(btn);
                            }}
                            trR.appendChild(tdAct);
                            
                            const tdSym = document.createElement('td'); tdSym.className = 'sym-cell'; tdSym.textContent = row.sym; trR.appendChild(tdSym);
                            const tdLn = document.createElement('td'); tdLn.className = 'ln-cell'; tdLn.textContent = row.ln2; trR.appendChild(tdLn);
                            const tdTxt = document.createElement('td'); tdTxt.innerHTML = row.f2_html; trR.appendChild(tdTxt);
                        }} else {{
                            trR.className = 'empty-line';
                            trR.innerHTML = '<td class="action-cell"></td><td class="sym-cell"></td><td class="ln-cell"></td><td></td>';
                        }}
                        rightTable.appendChild(trR);
                    }}

                    leftContainer.appendChild(leftTable);
                    centerContainer.appendChild(centerTable);
                    rightContainer.appendChild(rightTable);

                }} else {{
                    blockCount++;
                    const currentBlockIdx = blockCount;

                    const createAccordion = (text, targetContainer, tableContentGenerator) => {{
                        const details = document.createElement('details');
                        details.setAttribute('data-block-idx', currentBlockIdx);
                        
                        // Cross-column mirror toggle tracking engine
                        details.addEventListener('toggle', (e) => {{
                            const isOpen = details.open;
                            document.querySelectorAll(`details[data-block-idx="${{currentBlockIdx}}"]`).forEach(d => {{
                                if (d.open !== isOpen) d.open = isOpen;
                            }});
                        }});

                        const summary = document.createElement('summary');
                        summary.textContent = text;
                        details.appendChild(summary);
                        
                        const wrapper = document.createElement('div');
                        wrapper.style.overflowX = 'auto';
                        const table = tableContentGenerator();
                        wrapper.appendChild(table);
                        details.appendChild(wrapper);
                        targetContainer.appendChild(details);
                    }};

                    const label = 'Collapsed ' + block.length + ' matching lines';

                    createAccordion(label, leftContainer, () => {{
                        const t = document.createElement('table');
                        for(let i=block.startIndex; i<block.startIndex+block.length; i++) {{
                            const tr = document.createElement('tr'); tr.className='equal';
                            tr.innerHTML = '<td class="ln-cell">' + rawDiffData[i].ln1 + '</td><td class="sym-cell">=</td><td>' + rawDiffData[i].f1_html + '</td><td class="action-cell"></td>';
                            t.appendChild(tr);
                        }}
                        return t;
                    }});

                    createAccordion(label, centerContainer, () => {{
                        const t = document.createElement('table');
                        for(let i=block.startIndex; i<block.startIndex+block.length; i++) {{
                            const tr = document.createElement('tr'); tr.className='equal';
                            const tdLn = document.createElement('td'); tdLn.className = 'ln-cell'; tdLn.textContent = centerLineNumbers[i]; tr.appendChild(tdLn);
                            const tdAct = document.createElement('td'); tdAct.className = 'action-cell'; tr.appendChild(tdAct);
                            const tdTxt = document.createElement('td'); tdTxt.textContent = mergedState[i].text; tr.appendChild(tdTxt);
                            t.appendChild(tr);
                        }}
                        return t;
                    }});

                    createAccordion(label, rightContainer, () => {{
                        const t = document.createElement('table');
                        for(let i=block.startIndex; i<block.startIndex+block.length; i++) {{
                            const tr = document.createElement('tr'); tr.className='equal';
                            tr.innerHTML = '<td class="action-cell"></td><td class="sym-cell">=</td><td class="ln-cell">' + rawDiffData[i].ln2 + '</td><td>' + rawDiffData[i].f2_html + '</td>';
                            t.appendChild(tr);
                        }}
                        return t;
                    }});
                }}
            }});
        }}

        function saveMergedFile() {{
            const fileLines = [];
            mergedState.forEach(row => {{
                if (row.status === 'accepted' && row.text !== null) {{
                    fileLines.push(row.text);
                }}
            }});

            const fileContent = fileLines.join('\\n');
            const blob = new Blob([fileContent], {{ type: 'text/plain;charset=utf-8' }});
            const element = document.createElement('a');
            element.href = URL.createObjectURL(blob);
            element.download = "merged_output.txt";
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        }}

        renderPanels();
    </script>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Interactive merge workspace successfully created at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a 3-column side-by-side interactive merging suite.")
    parser.add_argument("file1", help="Path to original document")
    parser.add_argument("file2", help="Path to modified document")
    parser.add_argument("-o", "--output", default="docCompare.html", help="Output layout path")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file1) or not os.path.exists(args.file2):
        print("Error: Input files missing.")
    else:
        generate_merge_html(args.file1, args.file2, args.output)