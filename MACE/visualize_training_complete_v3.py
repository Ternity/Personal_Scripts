#!/usr/bin/env python3
"""
MACE训练可视化工具 - DFT vs 预测对比图
Author:  Ternity
Date: 2026-01-05
"""

import json
import logging
import os
from typing import Optional

import ase.io
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from mace import data
from mace.data.utils import Configuration
from mace.tools import utils, torch_geometric

# 配置
plt.rcParams.update({"font.size": 10})
logging.basicConfig(level=logging.INFO, format='%(message)s')

# 颜色和误差类型定义
COLORS = {"train": "#d62728", "valid": "#1f77b4", "test":  "#2ca02c"}
ERROR_TYPES = {
    "PerAtomRMSE": [("rmse_e_per_atom", "RMSE E/atom [meV]"), ("rmse_f", "RMSE F [meV/Å]")],
    "PerAtomRMSEstressvirials": [
        ("rmse_e_per_atom", "RMSE E/atom [meV]"),
        ("rmse_f", "RMSE F [meV/Å]"),
        ("rmse_stress", "RMSE Stress [meV/Å³]"),
    ],
}


def parse_training_log(path: str) -> pd.DataFrame:
    """解析训练日志"""
    results = [json.loads(line) for line in open(path, 'r') if line.strip()]
    return pd.DataFrame(results)


def load_model_and_data(model_path: str, data_path: str, device: str, batch_size: int):
    """加载模型和数据"""
    # 加载模型
    model = torch.load(model_path, map_location=device)
    model.eval().to(device)
    z_table = utils.AtomicNumberTable([int(z) for z in model.atomic_numbers])
    heads = getattr(model, 'heads', ["Default"])
    
    # 读取数据
    atoms_list = ase.io.read(data_path, index=":", format='extxyz')
    logging.info(f"加载 {len(atoms_list)} 个结构 从 {data_path}")
    
    # 转换为Configuration
    configs = []
    for atoms in atoms_list:
        config = Configuration(
            atomic_numbers=atoms.get_atomic_numbers(),
            positions=atoms.get_positions(),
            properties={},
            weight=atoms.info.get('Weight', 1.0),
            property_weights={},
            config_type=atoms.info.get('Config_type', 'Default'),
            pbc=atoms.pbc,
            cell=atoms.cell.array if hasattr(atoms.cell, 'array') else atoms.cell,
        )
        
        # 从calc.results提取数据（ASE Extended XYZ格式）
        if hasattr(atoms, 'calc') and hasattr(atoms.calc, 'results'):
            results = atoms.calc.results
            if 'energy' in results:
                config.properties['energy'] = float(results['energy'])
            if 'forces' in results: 
                config.properties['forces'] = np.array(results['forces'], dtype=float)
            if 'stress' in results:
                config.properties['stress'] = results['stress']
            if 'virials' in results:
                config.properties['virials'] = np.array(results['virials'], dtype=float)
        
        # 备用：从info/arrays提取
        if 'energy' not in config.properties:
            config.properties['energy'] = atoms.info.get('energy', 0.0)
        if 'forces' not in config.properties and 'forces' in atoms.arrays:
            config.properties['forces'] = atoms.arrays['forces']
        if 'virial' in atoms.info and 'virials' not in config.properties:
            virial_str = atoms.info['virial']
            if isinstance(virial_str, str):
                config.properties['virials'] = np.array([float(x) for x in virial_str.split()]).reshape(3, 3)
        
        configs.append(config)
    
    # 创建数据集
    dataset = [data.AtomicData.from_config(cfg, z_table, float(model.r_max), heads) for cfg in configs]
    data_loader = torch_geometric.dataloader.DataLoader(dataset, batch_size=batch_size, shuffle=False)
    
    logging.info(f"创建 {len(dataset)} 个AtomicData (batch_size={batch_size})")
    return model, data_loader, z_table


def run_inference(model: nn.Module, data_loader, device: str, compute_stress:  bool):
    """模型推理"""
    model_dtype = next(model.parameters()).dtype
    results = {
        "energy": {"reference":  [], "predicted": [], "reference_per_atom": [], "predicted_per_atom": []},
        "forces": {"reference": [], "predicted": []},
    }
    if compute_stress:
        results["stress"] = {"reference": [], "predicted": []}
        results["virials"] = {"reference":  [], "predicted": [], "reference_per_atom": [], "predicted_per_atom": []}
    
    if device.startswith('cuda'):
        torch.cuda.empty_cache()
    
    for i, batch in enumerate(data_loader):
        if i % 500 == 0 and i > 0:
            logging.info(f"  推理进度: {i}/{len(data_loader)}")
        
        batch = batch.to(device)
        
        # 转换数据类型并启用梯度
        for key in batch.keys:
            if isinstance(batch[key], torch.Tensor) and batch[key].is_floating_point():
                batch[key] = batch[key].to(dtype=model_dtype)
        
        batch_dict = batch.to_dict()
        if 'positions' in batch_dict:
            batch_dict['positions'].requires_grad_(True)
        
        # 前向传播
        output = model(batch_dict, training=False, compute_force=True, 
                      compute_stress=compute_stress, compute_virials=compute_stress)
        
        atoms_per_config = batch.ptr[1: ] - batch.ptr[:-1]
        
        # 保存结果
        if output.get("energy") is not None and batch.energy is not None:
            results["energy"]["reference"].append(batch.energy.detach().cpu())
            results["energy"]["predicted"].append(output["energy"].detach().cpu())
            results["energy"]["reference_per_atom"].append((batch.energy / atoms_per_config).detach().cpu())
            results["energy"]["predicted_per_atom"].append((output["energy"] / atoms_per_config).detach().cpu())
        
        if output.get("forces") is not None and batch.forces is not None:
            results["forces"]["reference"].append(batch.forces.detach().cpu())
            results["forces"]["predicted"].append(output["forces"].detach().cpu())
        
        if compute_stress:
            if output.get("stress") is not None and batch.stress is not None:
                results["stress"]["reference"].append(batch.stress.detach().cpu())
                results["stress"]["predicted"].append(output["stress"].detach().cpu())
            
            if output.get("virials") is not None and batch.virials is not None:
                results["virials"]["reference"].append(batch.virials.detach().cpu())
                results["virials"]["predicted"].append(output["virials"].detach().cpu())
                atoms_per_config_3d = atoms_per_config.view(-1, 1, 1)
                results["virials"]["reference_per_atom"].append((batch.virials / atoms_per_config_3d).detach().cpu())
                results["virials"]["predicted_per_atom"].append((output["virials"] / atoms_per_config_3d).detach().cpu())
        
        if device.startswith('cuda') and i % 50 == 0:
            torch.cuda.empty_cache()
    
    # 拼接结果
    for key in results: 
        for subkey in results[key]:
            if results[key][subkey]: 
                results[key][subkey] = torch.cat(results[key][subkey]).reshape(-1).numpy()
    
    return results


def plot_training_curves(ax_loss, ax_error, log_data:  pd.DataFrame, error_type: str, current_epoch: int):
    """绘制训练曲线"""
    if log_data.empty:
        return
    
    numeric_cols = log_data.select_dtypes(include=[np.number]).columns.tolist()
    
    valid_data = log_data[log_data["mode"] == "eval"].groupby(["mode", "epoch"])[numeric_cols].agg(["mean"]).reset_index()
    train_data = log_data[log_data["mode"] == "opt"].groupby(["mode", "epoch"])[numeric_cols].agg(["mean"]).reset_index()
    
    if train_data.empty or valid_data.empty:
        return
    
    # Loss
    ax_loss.plot(train_data["epoch"], train_data["loss"]["mean"], color=COLORS["train"], linewidth=2, label="Training")
    ax_loss.plot(valid_data["epoch"], valid_data["loss"]["mean"], color=COLORS["valid"], linewidth=2, label="Validation")
    ax_loss.axvline(current_epoch, color="black", linestyle="--", alpha=0.7)
    ax_loss.set_xlabel("Epoch", fontsize=12)
    ax_loss.set_ylabel("Loss", fontsize=12)
    ax_loss.set_yscale("log")
    ax_loss.legend(fontsize=10)
    ax_loss.grid(True, linestyle="--", alpha=0.4)
    
    # Errors
    error_labels = ERROR_TYPES.get(error_type, ERROR_TYPES["PerAtomRMSE"])
    colors_list = ["#2ca02c", "#ff7f0e", "#9467bd"]
    
    for i, (key, label) in enumerate(error_labels):
        if key in valid_data.columns:
            ax_error.plot(valid_data["epoch"], valid_data[key]["mean"] * 1e3, 
                         color=colors_list[i], linewidth=2, label=label)
    
    ax_error.axvline(current_epoch, color="black", linestyle="--", alpha=0.7)
    ax_error.set_xlabel("Epoch", fontsize=12)
    ax_error.set_ylabel("Error", fontsize=12)
    ax_error.set_yscale("log")
    ax_error.legend(fontsize=10)
    ax_error.grid(True, linestyle="--", alpha=0.4)


def plot_scatter(ax, ref, pred, xlabel, ylabel, title, color):
    """绘制散点图"""
    ax.scatter(ref, pred, alpha=0.6, s=20, color=color, edgecolors="none")
    
    min_val, max_val = min(ref.min(), pred.min()), max(ref.max(), pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2, alpha=0.7)
    
    rmse = np.sqrt(np.mean((ref - pred) ** 2))
    mae = np.mean(np.abs(ref - pred))
    ax.text(0.05, 0.95, f"RMSE: {rmse:.4f}\nMAE: {mae:.4f}", transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, linestyle="--", alpha=0.3)


def create_visualization(log_path: str, model_path: str, train_data_path: str, 
                        valid_data_path: Optional[str], output_path: str,
                        error_type: str, device: str, compute_stress: bool, batch_size: int):
    """创建可视化"""
    logging.info("=" * 60)
    logging.info("MACE 训练可视化工具")
    logging.info("=" * 60)
    
    # GPU信息
    if device.startswith('cuda') and torch.cuda.is_available():
        gpu_id = int(device.split(':')[-1]) if ':' in device else 0
        logging.info(f"GPU:  {torch.cuda.get_device_name(gpu_id)} ({torch.cuda.get_device_properties(gpu_id).total_memory / 1024**3:.1f} GB)")
    
    # 加载数据
    log_data = parse_training_log(log_path)
    current_epoch = int(log_data["epoch"].max())
    
    model, train_loader, _ = load_model_and_data(model_path, train_data_path, device, batch_size)
    logging.info("开始训练集推理...")
    train_results = run_inference(model, train_loader, device, compute_stress)
    
    valid_results = None
    if valid_data_path:
        _, valid_loader, _ = load_model_and_data(model_path, valid_data_path, device, batch_size)
        logging.info("开始验证集推理...")
        valid_results = run_inference(model, valid_loader, device, compute_stress)
    
    # 创建图表
    logging.info("生成可视化图表...")
    n_cols = 3 if compute_stress else 2
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, max(2, n_cols), hspace=0.3, wspace=0.3)
    
    # 训练曲线
    ax_loss = fig.add_subplot(gs[0, 0])
    ax_error = fig.add_subplot(gs[0, 1])
    plot_training_curves(ax_loss, ax_error, log_data, error_type, current_epoch)
    
    # 散点图
    ax_energy = fig.add_subplot(gs[1, 0])
    plot_scatter(ax_energy, train_results["energy"]["reference_per_atom"], 
                train_results["energy"]["predicted_per_atom"],
                "DFT Energy/atom [eV]", "MACE Energy/atom [eV]", "Energy per Atom", COLORS["train"])
    
    ax_force = fig.add_subplot(gs[1, 1])
    plot_scatter(ax_force, train_results["forces"]["reference"], train_results["forces"]["predicted"],
                "DFT Forces [eV/Å]", "MACE Forces [eV/Å]", "Atomic Forces", COLORS["train"])
    
    if compute_stress and train_results["virials"]["reference"].size > 0:
        ax_virial = fig.add_subplot(gs[1, 2])
        plot_scatter(ax_virial, train_results["virials"]["reference_per_atom"],
                    train_results["virials"]["predicted_per_atom"],
                    "DFT Virials/atom [eV]", "MACE Virials/atom [eV]", "Virials per Atom", COLORS["train"])
    
    fig.suptitle(f"MACE Training Visualization - Epoch {current_epoch}", fontsize=16, fontweight='bold', y=0.995)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logging.info(f"✅ 保存图表:  {output_path}")
    plt.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MACE训练可视化工具")
    parser.add_argument("--log", required=True, help="训练日志 (results.txt)")
    parser.add_argument("--model", required=True, help="模型检查点 (.model)")
    parser.add_argument("--train", required=True, help="训练数据 (.xyz)")
    parser.add_argument("--valid", help="验证数据 (.xyz)")
    parser.add_argument("--output", default="training_viz.png", help="输出图片")
    parser.add_argument("--error-type", default="PerAtomRMSE", choices=["PerAtomRMSE", "PerAtomRMSEstressvirials"])
    parser.add_argument("--device", default="cpu", help="设备 (cpu/cuda)")
    parser.add_argument("--stress", action="store_true", help="计算stress/virials")
    parser.add_argument("--batch-size", type=int, default=4, help="批次大小")
    parser.add_argument("--gpu", type=int, help="GPU编号")
    
    args = parser.parse_args()
    
    device = args.device
    if args.gpu is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpu)
        device = "cuda:0"
        logging.info(f"使用GPU {args.gpu}")
    
    create_visualization(
        log_path=args.log,
        model_path=args.model,
        train_data_path=args.train,
        valid_data_path=args.valid,
        output_path=args.output,
        error_type=args.error_type,
        device=device,
        compute_stress=args.stress,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()

'''
python visualize_training_complete.py \
    --log results/MACE-Omat-ft_run-3_train.txt \
    --model checkpoints/MACE-Omat-ft_run-3.model \
    --train train.xyz \
    --output training_visualization.png \
    --batch-size 16 \
    --device cuda \
    --gpu 4

python visualize_training_complete.py \
    --log results/results.txt \
    --model checkpoints/MACE_model_run-123.model \
    --train data/train.xyz \
    --stress \
    --error-type PerAtomRMSEstressvirials \
    --output training_with_virials.png

python visualize_training_complete.py \
    --log results/results.txt \
    --model checkpoints/MACE_model_run-123.model \
    --train data/train.xyz \
    --valid data/valid.xyz \
    --output full_visualization.png
'''