import argparse
import os
import sys
import logging
from protein_analyzer import ProteinAnalyzer
from hmmer_search import HMMERSearch
from cas_typing import CASTyping

def setup_logging(log_level='INFO', simplelog=False):
    """设置日志记录
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        simplelog: 若为True，则使用简单的日志格式
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' if not simplelog else '%(message)s'
    logging.basicConfig(level=numeric_level, format=log_format)

def main():
    parser = argparse.ArgumentParser(description='CRISPR-Cas Protein Predictor')
    parser.add_argument('input', help='Input FASTA file containing protein sequences')
    parser.add_argument('output', help='Output file to save predictions')
    parser.add_argument('--hmm_dir', help='Directory containing HMM models', 
                      default=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hmm_models'))
    parser.add_argument('--cas_types_file', help='JSON file with CAS type mapping information',
                      default=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cas_types.json'))
    parser.add_argument('--report', help='Generate detailed report file', default='')
    parser.add_argument('--log_lvl', help='Logging level', default='INFO', 
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--simplelog', help='Use simple log format', action='store_true')
    parser.add_argument('--min_length', help='Minimum protein length', type=int, default=50)
    parser.add_argument('--threads', help='并行处理使用的线程数', type=int, default=None)
    args = parser.parse_args()

    # 设置日志
    setup_logging(args.log_lvl, args.simplelog)
    
    try:
        logging.info(f"开始分析文件: {args.input}")
        logging.info(f"使用HMM模型目录: {args.hmm_dir}")
        
        # 步骤1: 分析蛋白质序列
        analyzer = ProteinAnalyzer(args.input)
        analyzer.filter_sequences(min_length=args.min_length)
        input_file = analyzer.write_filtered_sequences()
        logging.info(f"处理后的序列已保存至: {input_file}")
        
        # 步骤2: 使用HMMER搜索潜在的CRISPR-Cas蛋白
        hmmer_search = HMMERSearch(args.hmm_dir, num_threads=args.threads)
        potential_proteins = hmmer_search.search(input_file)
        logging.info(f"HMMER搜索完成，找到 {len(potential_proteins)} 个潜在的Cas蛋白")
        
        # 步骤3: 对识别出的CRISPR-Cas蛋白进行分类
        cas_types_file = args.cas_types_file if os.path.exists(args.cas_types_file) else None
        cas_typing = CASTyping(potential_proteins, cas_types_file)
        predictions = cas_typing.classify_proteins()
        
        # 步骤4: 保存预测结果到输出文件
        with open(args.output, 'w') as f:
            # 添加标题行
            f.write("protein_id\ttype\tconfidence\tprobability\te_value\tscore\thmm_model\n")
            for protein_id, prediction in predictions.items():
                f.write(f"{protein_id}\t{prediction['type']}\t{prediction['confidence']}\t"
                       f"{prediction['probability']:.1f}\t{prediction['e_value']:.4g}\t"
                       f"{prediction['score']}\t{prediction['hmm_model']}\n")
        
        logging.info(f"预测结果已保存至: {args.output}")
        
        # 生成详细报告（如果需要）
        if args.report:
            report = cas_typing.generate_report(args.report)
            logging.info(f"详细报告已保存至: {args.report}")
        
        logging.info("分析完成!")
        
    except Exception as e:
        logging.error(f"运行时出错: {e}")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())