"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { 
  Package, 
  Search, 
  Plus, 
  Edit3, 
  Trash2, 
  TrendingUp, 
  Tag, 
  SlidersHorizontal,
  DollarSign
} from "lucide-react"

interface Product {
  id: string
  sku: string | null
  name: str
  description: string | null
  category: string | null
  cost_price: number
  base_price: number
  current_price: number
  max_price: number | null
  min_price: number | null
  stock_qty: number
}

export default function ProductsPage() {
  const [products, setProducts] = React.useState<Product[]>([])
  const [loading, setLoading] = React.useState(true)
  const [search, setSearch] = React.useState("")
  const [categoryFilter, setCategoryFilter] = React.useState("")
  const [categories, setCategories] = React.useState<string[]>([])
  
  // Dialog / Modal state
  const [isDialogOpen, setIsDialogOpen] = React.useState(false)
  const [editingProduct, setEditingProduct] = React.useState<Product | null>(null)
  
  // Form states
  const [sku, setSku] = React.useState("")
  const [name, setName] = React.useState("")
  const [desc, setDesc] = React.useState("")
  const [category, setCategory] = React.useState("")
  const [cost, setCost] = React.useState("")
  const [base, setBase] = React.useState("")
  const [minPrice, setMinPrice] = React.useState("")
  const [maxPrice, setMaxPrice] = React.useState("")
  const [stock, setStock] = React.useState("0")
  const [formError, setFormError] = React.useState<string | null>(null)

  const fetchProducts = React.useCallback(async () => {
    setLoading(true)
    try {
      let url = "/products"
      const params = new URLSearchParams()
      if (search) params.append("search", search)
      if (categoryFilter) params.append("category", categoryFilter)
      if (params.toString()) url += `?${params.toString()}`

      const res = await apiFetch(url)
      if (res.ok) {
        const data = await res.json()
        setProducts(data)
        
        // Extract unique categories for filtering
        const uniqueCats: string[] = Array.from(
          new Set(data.map((p: Product) => p.category).filter(Boolean))
        )
        setCategories(uniqueCats)
      }
    } catch (err) {
      console.error("Failed to load products:", err)
    }
    setLoading(false)
  }, [search, categoryFilter])

  React.useEffect(() => {
    fetchProducts()
  }, [fetchProducts])

  const openAddDialog = () => {
    setEditingProduct(null)
    setSku("")
    setName("")
    setDesc("")
    setCategory("")
    setCost("")
    setBase("")
    setMinPrice("")
    setMaxPrice("")
    setStock("0")
    setFormError(null)
    setIsDialogOpen(true)
  }

  const openEditDialog = (product: Product) => {
    setEditingProduct(product)
    setSku(product.sku || "")
    setName(product.name)
    setDesc(product.description || "")
    setCategory(product.category || "")
    setCost(product.cost_price.toString())
    setBase(product.base_price.toString())
    setMinPrice(product.min_price?.toString() || "")
    setMaxPrice(product.max_price?.toString() || "")
    setStock(product.stock_qty.toString())
    setFormError(null)
    setIsDialogOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    const costNum = parseFloat(cost)
    const baseNum = parseFloat(base)
    const minNum = minPrice ? parseFloat(minPrice) : null
    const maxNum = maxPrice ? parseFloat(maxPrice) : null
    const stockNum = parseInt(stock) || 0

    if (isNaN(costNum) || isNaN(baseNum)) {
      setFormError("Cost and Base prices must be numbers.")
      return
    }

    if (minNum !== null && minNum < costNum) {
      setFormError("Floor price cannot be less than cost price floor.")
      return
    }

    if (maxNum !== null && maxNum < baseNum) {
      setFormError("Ceiling price cannot be less than base price baseline.")
      return
    }

    const payload = {
      sku: sku || null,
      name,
      description: desc || null,
      category: category || null,
      cost_price: costNum,
      base_price: baseNum,
      min_price: minNum,
      max_price: maxNum,
      stock_qty: stockNum
    }

    try {
      let res
      if (editingProduct) {
        res = await apiFetch(`/products/${editingProduct.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            ...payload,
            current_price: editingProduct.current_price > baseNum ? editingProduct.current_price : baseNum
          })
        })
      } else {
        res = await apiFetch("/products", {
          method: "POST",
          body: JSON.stringify(payload)
        })
      }

      if (res.ok) {
        setIsDialogOpen(false)
        fetchProducts()
      } else {
        const errorData = await res.json()
        setFormError(errorData.detail || "Transaction failed.")
      }
    } catch {
      setFormError("Failed to communicate with catalog server.")
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete ${name} from inventory?`)) return
    
    try {
      const res = await apiFetch(`/products/${id}`, {
        method: "DELETE"
      })
      if (res.ok) {
        fetchProducts()
      }
    } catch (err) {
      console.error("Delete call failed:", err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Search and Action Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Search fields */}
        <div className="flex flex-1 items-center space-x-2 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <Input
              placeholder="Search catalog by name or SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-40 shrink-0"
          >
            <option value="" className="bg-slate-900">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat} className="bg-slate-900">{cat}</option>
            ))}
          </Select>
        </div>

        <Button onClick={openAddDialog} variant="glow" className="flex items-center gap-1.5 self-start sm:self-center">
          <Plus className="h-4 w-4" />
          <span>Add Product</span>
        </Button>
      </div>

      {/* Catalog Table */}
      <Card className="border-slate-850 glass-card">
        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <div className="text-center py-20 text-slate-400 text-xs">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent mx-auto mb-2"></div>
              Loading catalog...
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-20 text-slate-500 text-sm">
              <Package className="h-10 w-10 text-slate-700 mx-auto mb-2" />
              No products found in catalog. Create one to begin.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-sm text-slate-300">
              <thead>
                <tr className="border-b border-slate-900 bg-slate-950/80 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <th className="px-6 py-4">Product details</th>
                  <th className="px-6 py-4">SKU / Category</th>
                  <th className="px-6 py-4 text-right">Cost floor</th>
                  <th className="px-6 py-4 text-right">Base price</th>
                  <th className="px-6 py-4 text-right">Current Price</th>
                  <th className="px-6 py-4 text-center">Safety Bounds</th>
                  <th className="px-6 py-4 text-center">Stock</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900">
                {products.map((product) => {
                  const hasDynamicPrice = roundPrice(product.current_price) !== roundPrice(product.base_price)
                  const isMarkup = product.current_price > product.base_price

                  return (
                    <tr key={product.id} className="hover:bg-slate-900/20 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white">{product.name}</div>
                        {product.description && (
                          <div className="text-xs text-slate-500 max-w-[200px] truncate">{product.description}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs font-mono text-slate-400">{product.sku || "N/A"}</div>
                        {product.category && (
                          <span className="inline-block text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-slate-500 border border-slate-800/80 mt-1 uppercase">
                            {product.category}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-slate-400">
                        ${product.cost_price.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-slate-400">
                        ${product.base_price.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className={`font-bold inline-block px-2.5 py-1 rounded text-sm ${
                          hasDynamicPrice
                            ? isMarkup
                              ? "bg-emerald-950/40 text-emerald-400 border border-emerald-500/20"
                              : "bg-amber-950/40 text-amber-400 border border-amber-500/20"
                            : "text-white"
                        }`}>
                          ${product.current_price.toFixed(2)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center text-xs text-slate-500 font-mono">
                        ${product.min_price?.toFixed(1) || "N/A"} - ${product.max_price?.toFixed(1) || "N/A"}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`inline-block font-bold text-xs px-2.5 py-1 rounded ${
                          product.stock_qty <= 10
                            ? "bg-red-950/40 text-red-400 border border-red-500/20"
                            : "bg-slate-900 text-slate-300"
                        }`}>
                          {product.stock_qty}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <button
                          onClick={() => openEditDialog(product)}
                          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 cursor-pointer inline-flex"
                        >
                          <Edit3 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(product.id, product.name)}
                          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400 cursor-pointer inline-flex"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* CRUD dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent onClose={() => setIsDialogOpen(false)} className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingProduct ? "Modify Product Details" : "Add New Store Item"}</DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            {formError && (
              <div className="text-xs font-semibold p-3 rounded-lg bg-red-950/20 border border-red-900/40 text-red-400">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">SKU (optional)</label>
                <Input placeholder="COF-LAT-LG" value={sku} onChange={(e) => setSku(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Product Category</label>
                <Input placeholder="Beverages" value={category} onChange={(e) => setCategory(e.target.value)} />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400 font-medium">Product Name</label>
              <Input placeholder="Vanilla Latte" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400 font-medium">Description</label>
              <Input placeholder="Signature espresso brew..." value={desc} onChange={(e) => setDesc(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Cost Price ($)</label>
                <Input placeholder="1.20" value={cost} onChange={(e) => setCost(e.target.value)} required />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Base Retail Price ($)</label>
                <Input placeholder="4.50" value={base} onChange={(e) => setBase(e.target.value)} required />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 border-t border-slate-900 pt-3">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Min Floor Limit ($)</label>
                <Input placeholder="3.50 (optional)" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Max Ceiling Limit ($)</label>
                <Input placeholder="6.50 (optional)" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-400 font-medium">Initial Stock Quantity</label>
              <Input type="number" value={stock} onChange={(e) => setStock(e.target.value)} required />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="glow">
                {editingProduct ? "Save Changes" : "Create Item"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function roundPrice(val: number): number {
  return Math.round(val * 100) / 100
}
