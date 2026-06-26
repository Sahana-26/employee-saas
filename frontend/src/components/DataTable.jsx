import React from 'react'
export default function DataTable({ columns, rows }) {
  return (
    <div className="tableCard">
      <table>
        <thead>
          <tr>{columns.map(col => <th key={col.key}>{col.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.id}>
              {columns.map(col => <td key={col.key}>{col.render ? col.render(row) : row[col.key]}</td>)}
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={columns.length}>No records found</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
