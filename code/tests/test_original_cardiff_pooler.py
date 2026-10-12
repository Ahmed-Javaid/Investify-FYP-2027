"""Native pooler retention on tiny tensor fixtures; no publisher quality claim."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investify.sentiment_receipts import original_cardiff_model_class, normalize_loading_info, validate_class_metadata

class OriginalCardiffPoolerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from transformers import RobertaConfig
        torch.set_num_threads(2)
        cls.torch = torch
        cls.config = RobertaConfig(vocab_size=64,hidden_size=16,num_hidden_layers=1,
            num_attention_heads=2,intermediate_size=32,max_position_embeddings=32,
            hidden_dropout_prob=0.,attention_probs_dropout_prob=0.,num_labels=3,
            id2label={0:'negative',1:'neutral',2:'positive'},label2id={'negative':0,'neutral':1,'positive':2})
        cls.config._attn_implementation='eager'
        cls.Model = original_cardiff_model_class()

    def model(self):
        self.torch.manual_seed(42)
        model = self.Model(self.config)
        model.eval()
        return model

    def test_original_pooler_parameters_are_present_in_the_loadable_architecture(self):
        model=self.model()
        self.assertIn('roberta.pooler.dense.weight',model.state_dict())
        self.assertIn('roberta.pooler.dense.bias',model.state_dict())

    def test_pooler_presence_and_values_cannot_change_classification_logits(self):
        model=self.model()
        ids=self.torch.tensor([[0,4,5,2],[0,7,8,2]])
        with self.torch.inference_mode():
            original=model(input_ids=ids).logits
            model.roberta.pooler.dense.weight.fill_(100.)
            model.roberta.pooler.dense.bias.fill_(-100.)
            modified=model(input_ids=ids).logits
            model.roberta.pooler=None
            removed=model(input_ids=ids).logits
        self.assertTrue(self.torch.equal(original,modified))
        self.assertTrue(self.torch.equal(original,removed))

    def test_full_checkpoint_loads_with_no_missing_unexpected_or_mismatched_keys(self):
        model=self.model()
        with tempfile.TemporaryDirectory(prefix='investify-native-pooler-fixture-') as directory:
            model.save_pretrained(directory,safe_serialization=True)
            loaded,info=self.Model.from_pretrained(directory,local_files_only=True,use_safetensors=True,output_loading_info=True)
            info=normalize_loading_info(info)
            self.assertTrue(all(not values for values in info.values()))
            for name,value in model.state_dict().items():
                self.assertTrue(self.torch.equal(value,loaded.state_dict()[name]),name)

    def test_missing_classifier_head_is_still_refused(self):
        from safetensors.torch import save_file
        model=self.model()
        with tempfile.TemporaryDirectory(prefix='investify-native-pooler-refusal-fixture-') as directory:
            path=Path(directory)
            self.config.save_pretrained(path)
            state={name:value.detach().contiguous().clone() for name,value in model.state_dict().items()
                   if name!='classifier.out_proj.bias'}
            save_file(state,str(path/'model.safetensors'),metadata={'format':'pt'})
            loaded,info=self.Model.from_pretrained(path,local_files_only=True,use_safetensors=True,output_loading_info=True)
            labels={'0':'negative','1':'neutral','2':'positive'}
            with self.assertRaisesRegex(ValueError,'must be empty'):
                validate_class_metadata(loaded.config,normalize_loading_info(info),labels,labels)


if __name__=='__main__':
    unittest.main()
