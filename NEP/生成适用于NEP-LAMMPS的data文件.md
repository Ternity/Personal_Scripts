## 最新方法
[NEP_CPU](https://github.com/brucefan1983/NEP_CPU)已经支持了自动元素映射和hybrid力场方法，具体见NEP_CPU文档的[use-the-nep-lammps-interface](https://github.com/brucefan1983/NEP_CPU?tab=readme-ov-file#use-the-nep-lammps-interface)部分。下面我也简要的说一下元素映射方法：

假设你有两个力场文件:<br>
第一个力场`nep_CNFeOH.txt`,元素顺序（第一行）为`C`, `N`, `Fe`, `O` and `H`;<br>
第二个力场`nep_water.txt`, 元素顺序为`H` and `O`。<br>
<br>
你有三个结构文件:<br>
第一个data文件`FeN4-C.data`，其中的atom type依次为`C`, `N`, `Fe`;<br>
第二个data文件`water.data`，其中的atom type依次为`O`, `H`;<br>
第三个data文件`FeN4-C-sol.data`，其中的atom type依次为`C`, `Fe`, `H`, `N` and `O`。<br>
<br>

### 案例1
对于第一个结构文件`FeN4-C.data`，必须使用`nep_CNFeOH.txt`力场，in文件写为：<br>
```bash
pair_style nep   
pair_coeff * *  nep_CNFeOH.txt C N Fe
```
因为力场文件中元素顺序和data文件中atom type顺序一致，所以pair_coeff后面的元素顺序没有修改。<br>

### 案例2
对于第二个结构文件`water.data`，提供的两个力场文件均可使用，in文件分别写为：<br>
```bash
# 使用nep_CNFeOH.txt
pair_style nep   
pair_coeff * *  nep_CNFeOH.txt O H
```
注意这里力场文件元素顺序(`H` `O`)和结构文件元素顺序(`O` `H`)相反。用户需要根据结构文件顺序修改力场文件路径后面的元素顺序<br>

```bash
# 使用nep_water.txt
pair_style nep   
pair_coeff * *  nep_water.txt O H
```
同样的，这里力场文件元素顺序(`C`, `N`, `Fe`, `O` and `H`)和结构文件元素顺序(`O` `H`)不同。用户仅需要根据结构文件顺序修改`pair_coeff`命令的力场文件路径后面的元素顺序即可<br>

### 案例3
对于第三个结构文件`FeN4-C-sol.data`，可以仅使用`nep_CNFeOH.txt`力场，也可以使用`nep_CNFeOH.txt`力场描述`C` `N` `Fe`元素间多体相互作用，使用`nep_water.txt`描述`O` `H`之间多体相互作用，而`C` `N` `Fe`和`O` `H`之间作用使用其他力场或`L-J`之类作用描述。in文件分别写为：<br>
```bash
# 单独使用nep_CNFeOH.txt
pair_style nep   
pair_coeff * *  nep_CNFeOH.txt C Fe H N O
```
注意力场文件元素顺序(`C` `N` `Fe` `O` `H`)和结构文件元素顺序(`C` `Fe` `H` `N` `O`)相反。用户需要根据结构文件顺序修改力场文件路径后面的元素顺序<br>            1   2    3   4   5

```bash
# 使用nep_CNFeOH.txt 混合 nep_water.txt
pair_style hybrid/overlay nep nep lj/cut 10
pair_coeff * *  nep 1 nep_CNFeOH.txt C Fe NULL N NULL
pair_coeff * *  nep 2 nep_water.txt  NULL NULL H NULL O 
# 这里我们将界面间各type相互作用简化为界面整体和水的作用，即指定type 1 2 4(C Fe N)与type 3 5(H O)之间作用。由于type 3和5不是连续编号，那只能分开写
pair_coeff 1*2 3 lj/cut 1.0 1.0
pair_coeff 1*2 5 lj/cut 1.0 1.0
pair_coeff  4  3 lj/cut 1.0 1.0
pair_coeff  4  5 lj/cut 1.0 1.0
```
两个星号 `* *`意味着每种atom type将被设置为一种力场中元素或`NULL`. `NULL`意味着这个力场不考虑这种（与data文件顺序相对应，因为前面使用了`* *`）atom type.<br>
`pair_coeff * *  nep 1 nep_CNFeOH.txt C Fe NULL N NULL` 意味着将考虑 `C-C` `C-Fe` `C-N` `Fe-Fe` `Fe-N` `N-N` 之间的相互作用.<br>

## 背景

在使用NEP-CPU-LAMMPS时候，atom的`type`必须与力场文件`nep.txt`的第一行类型顺序一致。假设，`nep.txt`文件第一行为：

```
nep4 5 C N Fe O H
```

那么，atom的`type`顺序必须为：

```
C atom to type 1
N atom to type 2
Fe atom to type 3
O atom to type 4
H atom to type 5
```

如果结构文件中只有部分元素，那么应当缺省不存在的元素的type，以上面的力场文件为例：

假设结构文件中只有O atom 和 H atom，那么，它们的type应当设置为：

```
O atom to type 4
H atom to type 5
```

经过测试，发现无法只修改LAMMPS的输入文件(in.lammps), 在其中设置一个data文件中不存在的type。但是可以只修改data文件或者同时修改data文件和in文件实现元素映射。

## 映射方法

### 方法一：同时修改`data`文件和`in`文件

#### data文件修改方法

沿用背景的假设，力场包含5种元素，那么对于`data`文件，`n atom types`，n必须等于5。自然，下面的`Masses`部分，也需要指定5种type，且顺序与力场文件相同。对于`Atoms`部分，无需任何修改，和原始data文件保持一致即可，下面是`data`文件的一部分：

```
LAMMPS data file

180 atoms
5 atom types

0.418993006087244 10.691006993913204 xlo xhi
0.534132045962215 12.4758679540383 ylo yhi
-0.05786291282208644 16.057862912819132 zlo zhi

 Masses
 
 1 12.01099999691024
 2 14.00699999639678
 3 55.84499998563419
 4 15.99899999588435
 5 1.007999999740698
 
 Atoms # atomic
 
 1 2 3.174390239466599 3.6603033253093273 1.1249652324643646 # need O
 2 1 4.239805063185599 2.5664785458997605 2.142761035900666 # need H
 3 1 2.5030635721189975 3.805549055908386 1.7471340718357349 # need H
```

#### in文件修改方法

在`in`文件中，需要利用type转换将`data`文件里的`Atoms`部分的type 1 转化为 type 5(C to H)，type 2 转化为type 4(N to O)。那么我们使用set命令实现：

```
read_data       ${fname}
set             type 1          type 5              # C to H
set             type 2          type 4              # N to O
group           group_H         type 5              # atom H type 5
group           group_O         type 4              # atom O type 4
group           water           type 4 5            # 合并group的方法
```

然后就如同正常的设置一样使用，记得`dump_modify` 元素映射要写全：C N Fe O H



### 方法二：只修改`data`文件

同样沿用背景的假设，力场包含5种元素，那么对于`data`文件，`n atom types`，n必须等于5。自然，下面的`Masses`部分，也需要指定5种type，且顺序与力场文件相同。对于`Atoms`部分，只需将原始type转换为应当对应的元素type即可，转换方法利用[转换code](onenote:#生成适用于NEP-LAMMPS的data文件&section-id={72DE9FFF-2BBE-4E09-A15C-A05FEDCCC475}&page-id={949F92A0-3740-4D14-84DB-BBBB3285FEF8}&object-id={C7E43631-D548-4A5F-B138-A0FEED2564F9}&FD&base-path=https://njfueducn-my.sharepoint.com/personal/180401224_njfu_edu_cn/Documents/笔记本/各种参考资料/使用方法/ASE.one)实现。下面是转换后`data`文件的一部分：

```
LAMMPS data file， contain one water molecule

180 atoms
5 atom types

0.418993006087244 10.691006993913204 xlo xhi
0.534132045962215 12.4758679540383 ylo yhi
-0.05786291282208644 16.057862912819132 zlo zhi

Masses
 
 1 12.01099999691024
 2 14.00699999639678
 3 55.84499998563419
 4 15.99899999588435
 5 1.007999999740698
 
Atoms # atomic
 
 1 4 3.174390239466599 3.6603033253093273 1.1249652324643646
 2 5 4.239805063185599 2.5664785458997605 2.142761035900666
 3 5 2.5030635721189975 3.805549055908386 1.7471340718357349
```

在\`in\`文件中，不需要使用\`set\`命令实现type映射，只需直接设置group为相应type（当然，没有需求可以不设置），下面是\`in\`文件的一部分：

```
read_data       ${fname}
group           group_H         type 5              # atom H type 5
group           group_O         type 4              # atom O type 4
group           water           type 4 5            # 合并group的方法
```

## 最优方法

根据[转换code](onenote:#生成适用于NEP-LAMMPS的data文件&section-id={72DE9FFF-2BBE-4E09-A15C-A05FEDCCC475}&page-id={949F92A0-3740-4D14-84DB-BBBB3285FEF8}&object-id={C7E43631-D548-4A5F-B138-A0FEED2564F9}&FD&base-path=https://njfueducn-my.sharepoint.com/personal/180401224_njfu_edu_cn/Documents/笔记本/各种参考资料/使用方法/ASE.one)部分的分析，其实，甚至不需要修改任何代码或者使用自编脚本，只需使用ase的`write_lammps_data`函数,`specorder`参数必须指定为nep力场元素顺序列表，然后手动修改`data`文件的`Masses`部分为nep力场元素列表即可。

### 附录：转换code

在ase的`write_lammps_data` 函数的基础上，`specorder`参数必须指定为nep力场元素顺序列表，`_write_masses`函数的`if s not in symbols_indices:`部分改为`mass = float(Atoms(s)[0].mass)`并写入Masses部分，下面是`_write_masses`函数修改后：

```
# mapping.py
# change type according to nep.txt first line

def _write_masses(fd, atoms: Atoms, species: list, units: str):
    symbols_indices = atoms.symbols.indices()       # return a dict {'element_symbol_1': array([a,b,c,...]), 'element_symbol_2': array([x,y,z,...])}
   fd.write("Masses\n\n")
   for i, s in enumerate(species):
       # Find the first atom of the element `s` and extract its mass
       if s not in symbols_indices:
            # Still write mass if the system does not contain the element `s`.
            # Cover by `float` to make a new object for safety
            mass = float(Atoms(s)[0].mass)
            # Convert mass from ASE units to LAMMPS units
            mass = convert(mass, "mass", "ASE", units)
            atom_type = i + 1
            fd.write(f"{atom_type:>6} {mass:23.17g} # {s}\n")
        else:
            # Cover by `float` to make a new object for safety
            mass = float(atoms[symbols_indices[s][0]].mass)
            # Convert mass from ASE units to LAMMPS units
            mass = convert(mass, "mass", "ASE", units)
            atom_type = i + 1
            fd.write(f"{atom_type:>6} {mass:23.17g} # {s}\n")
    fd.write("\n")
```

